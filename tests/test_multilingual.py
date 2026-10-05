import asyncio
import json
from types import SimpleNamespace

import pytest
from app import inference
from app.models import Understanding, validate_understanding
from app.quality import recap_checks, wording_checks, anchor_relative_dates
from datetime import datetime
from app.models import Action


def test_native_daypart_not_erased_by_english_guard():
    source = 'நாளை மாலை ஏழு மணிக்கு சந்திப்போம்.'
    result = Understanding(title='Meeting', recap='', actions=[dict(
        type='event', title='Meeting', evidence=source, date='2026-10-06',
        time='19:00', duration_minutes=30)])
    assert validate_understanding(result, source).actions[0].time == '19:00'


def test_english_punctuation_does_not_bypass_ambiguous_hour():
    source = 'Meet tomorrow at six… actually seven.'
    result = Understanding(title='Meeting', recap='', actions=[dict(
        type='event', title='Meeting', evidence=source, date='2026-10-06',
        time='19:00', duration_minutes=30)])
    assert validate_understanding(result, source).actions[0].time == ''


def test_native_script_alone_does_not_prove_am_pm():
    source = 'நாளை ஏழு மணிக்கு சந்திப்போம்.'
    result = Understanding(title='Meeting', recap='', actions=[dict(
        type='event', title='Meeting', evidence=source, date='2026-10-06',
        time='19:00', duration_minutes=30)])
    assert validate_understanding(result, source).actions[0].time == ''


def test_clipped_hindi_evidence_cannot_hide_later_prohibition():
    source = 'HDMI adapter 800 रुपये से कम का चाहिए, लेकिन अभी मत खरीदो।'
    result = Understanding(title='Shopping', recap='', actions=[dict(
        type='shopping', title='Adapter', evidence='HDMI adapter 800', budget_inr=800)])
    action = validate_understanding(result, source).actions[0]
    assert action.certainty == 'conditional' and action.status == 'needs clarification'


def test_language_issue_blocks_affected_action_and_requires_real_quote():
    source = 'Bring the proton type.'
    result = Understanding(title='Bring it', recap=source, actions=[dict(
        type='task', title='Bring prototype', evidence=source)],
        language_issues=[dict(quote='proton type', reason='Did you mean prototype?', suggestion='prototype')])
    assert validate_understanding(result, source).actions[0].status == 'needs clarification'
    result.language_issues[0].quote = 'not in transcript'
    with pytest.raises(ValueError, match='language review'):
        validate_understanding(result, source)


def test_output_language_and_asr_context_reach_gemma(monkeypatch):
    monkeypatch.setattr(inference, 'config', lambda: ('ollama', 'gemma4:e2b'))
    async def generate(prompt, schema):
        assert '"output_language": "Tamil"' in prompt
        assert '"primary_language": "ta"' in prompt
        if schema['title'] == 'RecapReview':
            return json.dumps({'recap':'நாளை சந்திப்போம்.', 'detected_languages':['Tamil', 'English'], 'language_issues':[]})
        return json.dumps({'title':'Meeting','recap':'நாளை சந்திப்போம்.', 'actions':[]})
    monkeypatch.setattr(inference, 'generate', generate)
    result = asyncio.run(inference.understand('Naalai meet pannalam.',
        '2026-10-05T09:00:00+05:30', 'Asia/Kolkata', 'concise', 'Tamil', {'primary_language':'ta'}))
    assert result.detected_languages == ['Tamil', 'English']


def test_asr_multilingual_settings_and_uncertainty_metadata(monkeypatch):
    import faster_whisper.audio
    monkeypatch.setattr(inference, 'load_dotenv', lambda **kw: None)
    monkeypatch.setenv('WHISPER_MODEL', 'large-v3-turbo')
    monkeypatch.setenv('WHISPER_DEVICE', 'cpu')
    monkeypatch.setenv('WHISPER_COMPUTE', 'int8')
    monkeypatch.setattr(faster_whisper.audio, 'decode_audio', lambda *a, **k: [0] * 16000)
    class Speech:
        def transcribe(self, audio, **kwargs):
            assert kwargs['language'] is None and kwargs['multilingual'] is True
            assert kwargs['task'] == 'transcribe' and kwargs['word_timestamps'] is True
            segment = SimpleNamespace(start=0, end=1, text='நாளை meeting', avg_logprob=-0.9,
                words=[SimpleNamespace(word=' meeting', start=0.5, end=1, probability=0.3)])
            return iter([segment]), SimpleNamespace(language='ta', language_probability=0.8)
    monkeypatch.setattr(inference, '_whisper', Speech())
    monkeypatch.setattr(inference, '_whisper_config', ('large-v3-turbo', 'cpu', 'int8'))
    result = inference.transcribe('unused.wav')
    assert result['raw_transcript'] == result['transcript'] == 'நாளை meeting'
    assert result['speech_warnings'][0]['words'] == ['meeting']
    assert result['language_probability'] == 0.8


def test_recap_discrepancies_detect_lost_conditions_dates_and_script():
    warnings = recap_checks('Maybe meet tomorrow. Do not buy yet.', 'Meet and buy.', [], 'original')
    assert len(warnings) == 3
    assert recap_checks('நாளை சந்திப்போம்.', 'Meet tomorrow.', [], 'original')
    assert not recap_checks('நாளை சந்திப்போம்.', 'Meet tomorrow.', [], 'English')


def test_split_term_consistency_flags_require_an_existing_near_match():
    issues = wording_checks('Bring the proton type to the prototype demo.')
    assert issues[0]['quote'] == 'proton type' and issues[0]['suggestion'] == 'prototype'
    assert not wording_checks('Bring the proton type.')
    assert not wording_checks('Bring the prototype tomorrow.')


def test_tanglish_relative_date_uses_recording_date_not_model_guess():
    action = Action(type='event', title='Meet', evidence='Naalai evening 7 mani ku meet pannalam.', date='2026-10-05')
    anchor_relative_dates([action], datetime.fromisoformat('2026-10-05T10:00:00+05:30'))
    assert action.date == '2026-10-06'
    action.evidence = 'Tomorrow, actually next Monday.'
    action.date = '2026-10-05'
    anchor_relative_dates([action], datetime.fromisoformat('2026-10-05T10:00:00+05:30'))
    assert not action.date and action.missing


def test_gemma_repairs_flagged_recap_once(monkeypatch):
    monkeypatch.setattr(inference, 'config', lambda: ('ollama', 'gemma4:e2b'))
    calls = []
    async def generate(prompt, schema):
        calls.append(schema['title'])
        if schema['title'] == 'Extraction':
            return json.dumps({'title':'Invite', 'recap':'', 'actions':[]})
        return json.dumps({'recap': 'Maybe invite Rahul.' if 'Possible fidelity discrepancies' in prompt else 'Invite Rahul.',
            'detected_languages':['English'], 'language_issues':[]})
    monkeypatch.setattr(inference, 'generate', generate)
    result = asyncio.run(inference.understand('Maybe invite Rahul.', '2026-10-05T09:00:00+05:30', 'Asia/Kolkata', 'concise'))
    assert result.recap == 'Maybe invite Rahul.' and not result.recap_warnings
    assert calls == ['Extraction', 'RecapReview', 'RecapReview']
