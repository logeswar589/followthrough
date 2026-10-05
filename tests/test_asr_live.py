"""Opt-in real ASR checks. RUN_ASR_TESTS=1 pytest tests/test_asr_live.py
Run scripts/make_demo.ps1 first to generate the Windows synthetic fixture.
"""
import os
from pathlib import Path
import wave
import pytest

pytestmark = pytest.mark.skipif(os.getenv('RUN_ASR_TESTS') != '1', reason='Opt-in: loads/downloads a real Whisper model')

def test_real_silence(tmp_path):
    from app.inference import transcribe
    path=tmp_path/'silence.wav'
    with wave.open(str(path),'wb') as audio:
        audio.setparams((1,2,16000,0,'NONE','not compressed'))
        audio.writeframes(bytes(16000*2*3))
    with pytest.raises(ValueError, match='No speech'):
        transcribe(path)

def test_synthetic_english_speech():
    from app.inference import transcribe
    path=Path('artifacts/synthetic-demo.wav')
    assert path.exists(), 'Run scripts/make_demo.ps1 first'
    result=transcribe(path)
    text=result['transcript'].lower()
    assert '800' in text and 'hdmi' in text and 'prototype' in text
    assert 'wait' in text and 'maybe' in text and 'rahul' in text
    assert result['segments'] and result['language']=='en'
