import importlib
import json
import pytest
from fastapi.testclient import TestClient
from app.models import Action, Understanding, validate_understanding
from app.calendar import calendar_export

def event(**kwargs):
    return Action(type='event', title='Prototype review', evidence='Meet tomorrow at seven PM.', id='test', date='2026-10-06', time='19:00', duration_minutes=30, **kwargs)

def test_calendar_timezone_and_alarm():
    output = calendar_export(event(reminder_minutes=30))
    assert 'DTSTART:20261006T133000Z' in output
    assert 'DTEND:20261006T140000Z' in output
    assert 'TRIGGER:-PT30M' in output
    assert '\r\n' in output

def test_calendar_escaping_and_line_folding():
    action = event()
    action.title = 'Tamil தமிழ் ' * 15 + '\nBEGIN:VEVENT'
    output = calendar_export(action)
    assert all(len(line.encode()) <= 75 for line in output.split('\r\n'))
    assert output.count('\r\nBEGIN:VEVENT') == 1

@pytest.mark.parametrize('certainty', ['conditional', 'tentative'])
def test_uncertainty_cannot_execute(certainty):
    action = event(certainty=certainty)
    result = validate_understanding(Understanding(title='test', recap='', actions=[action]), action.evidence)
    assert result.actions[0].status == 'needs clarification'
    with pytest.raises(ValueError):
        calendar_export(result.actions[0])

def test_missing_time_and_duration_block_export():
    action = event()
    action.time, action.duration_minutes = '', None
    validate_understanding(Understanding(title='test',recap='',actions=[action]),action.evidence)
    assert len(action.missing) == 2
    with pytest.raises(ValueError):
        calendar_export(action)

def test_invented_evidence_rejected():
    with pytest.raises(ValueError):
        validate_understanding(Understanding(title='test',recap='',actions=[event()]), 'Maybe meet later.')

def test_model_cannot_mark_action_completed():
    action = event(status='completed')
    validate_understanding(Understanding(title='test',recap='',actions=[action]),action.evidence)
    assert action.status == 'ready'

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('FOLLOWTHROUGH_DATA', str(tmp_path))
    import app.main
    module = importlib.reload(app.main)
    return TestClient(module.app), module

def test_api_persistence_edit_and_stale_actions(client, monkeypatch):
    client, module = client
    body = {'transcript':'Meet tomorrow at seven PM.', 'recorded_at':'2025-01-02T10:00:00+05:30'}
    item = client.post('/api/conversations',json=body).json()
    cid = item['id']
    async def fake(*args):
        assert args[1] == body['recorded_at']  # Old recording date passed unchanged.
        return Understanding(title='Meeting',recap='Meet at seven.',actions=[event()])
    monkeypatch.setattr(module,'understand',fake)
    result = client.post(f'/api/conversations/{cid}/understand').json()
    aid = result['actions'][0]['id']
    assert client.get(f'/api/conversations/{cid}/actions/{aid}/calendar').status_code == 200
    assert client.get(f'/api/conversations/{cid}').json()['actions'][0]['title']=='Prototype review'
    result = client.put(f'/api/conversations/{cid}/transcript',json={**body,'transcript':'Actually do not meet.'}).json()
    assert result['actions'] == []
    assert result['previous_analysis']['actions']
    assert result['analysis_history'][0]['transcript'] == body['transcript']
    assert client.get(f'/api/conversations/{cid}/actions/{aid}/calendar').status_code == 404

def test_bad_input_and_origin(client):
    client, _ = client
    assert client.post('/api/conversations',json={'recorded_at':'nonsense'}).status_code == 422
    assert client.post('/api/conversations',json={'recorded_at':'2026-10-05T10:00:00'}).status_code == 422
    assert client.post('/api/conversations',headers={'origin':'https://evil.example'},json={}).status_code == 403
    assert client.get('/api/health',headers={'host':'evil.example'}).status_code == 403
    assert client.post('/api/conversations',json={'recorded_at':'2026-10-05T10:00:00+05:30','timezone':'Not/AZone'}).status_code == 422

def test_silence_and_failed_extraction_preserve_original(client, monkeypatch):
    client,module = client
    item=client.post('/api/conversations',json={'recorded_at':'2026-10-05T10:00:00+05:30','transcript':'Original words.'}).json()
    cid=item['id']
    async def invalid(*args):
        raise ValueError('Malformed model output')
    monkeypatch.setattr(module,'understand',invalid)
    assert client.post(f'/api/conversations/{cid}/understand').status_code == 422
    assert client.get(f'/api/conversations/{cid}').json()['transcript']=='Original words.'
    assert client.post(f'/api/conversations/{cid}/audio',files={'file':('bad.exe',b'test')}).status_code==415
    assert client.post(f'/api/conversations/{cid}/audio',files={'file':('empty.wav',b'')}).status_code==422

@pytest.mark.parametrize('date,time', [('2026-03-08','02:30'),('2026-11-01','01:30')])
def test_dst_ambiguous_and_nonexistent_times(date,time):
    action=event(timezone='America/New_York')
    action.date,action.time=date,time
    with pytest.raises(ValueError):
        calendar_export(action)

def test_question_can_be_resolved_in_human_review():
    action=Action(type='question',title='Which port?',evidence='Confirm the laptop port.',details='USB-C confirmed')
    validate_understanding(Understanding(title='test',recap='',actions=[action]),action.evidence,reviewed=True)
    assert action.status=='ready'

def test_recap_without_actions_is_invalidated_after_transcript_edit(client):
    client,module=client
    body={'recorded_at':'2026-10-05T09:00:00+05:30','transcript':'I enjoyed the workshop.'}
    item=client.post('/api/conversations',json=body).json()
    cid=item['id']
    client.put(f'/api/conversations/{cid}/recap',json={'recap':'Enjoyed the workshop.'})
    edited=client.put(f'/api/conversations/{cid}/transcript',json={**body,'transcript':'I missed the workshop.'}).json()
    assert edited['recap']==''
    assert edited['analysis_history'][0]['recap']=='Enjoyed the workshop.'

def test_audio_decoder_accepts_silent_wav(tmp_path):
    # Decode/VAD path is exercised against a real silent WAV using the installed model.
    # Keep expensive model loading in the explicit integration suite instead.
    import wave
    path=tmp_path/'silent.wav'
    with wave.open(str(path),'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b'\0' * 32000)
    from faster_whisper.audio import decode_audio
    result=decode_audio(str(path),sampling_rate=16000)
    assert len(result)==16000 and not result.any()

def test_model_guess_of_am_is_cleared_but_human_can_confirm():
    action=event()
    action.evidence='Meet tomorrow at seven.'
    action.time='07:00'
    validate_understanding(Understanding(title='Meeting',recap='',actions=[action]),action.evidence)
    assert action.time=='' and action.status=='needs clarification'
    action.time='19:00'
    action.missing=[]
    validate_understanding(Understanding(title='Meeting',recap='',actions=[action]),action.evidence,reviewed=True)
    assert action.time=='19:00' and action.status=='ready'

def test_qualifier_before_short_quote_is_preserved():
    transcript='Maybe invite Rahul and send him a recap.'
    action=Action(type='draft',title='Recap for Rahul',evidence='send him a recap')
    validate_understanding(Understanding(title='Plans',recap='',actions=[action]),transcript)
    assert action.certainty=='tentative' and action.status=='needs clarification'

def test_prohibited_draft_is_not_ready():
    action=Action(type='draft',title='Recap',evidence='Do not send the recap yet.')
    validate_understanding(Understanding(title='Plans',recap='',actions=[action]),action.evidence)
    assert action.certainty=='conditional' and action.status=='needs clarification'

def test_asr_pm_without_space_is_preserved():
    action=event()
    action.evidence='Meet tomorrow at 6. Actually 7pm for 30 minutes.'
    validate_understanding(Understanding(title='Meeting',recap='',actions=[action]),action.evidence)
    assert action.time=='19:00'

def test_adjacent_shopping_condition_blocks_search():
    action=Action(type='shopping',title='HDMI adapter',evidence='We need an HDMI adapter under 800 rupees.',budget_inr=800)
    transcript=action.evidence+' Wait until we confirm the laptop port.'
    validate_understanding(Understanding(title='Shopping',recap='',actions=[action]),transcript)
    assert action.certainty=='conditional' and action.status=='needs clarification'


def test_uncertain_audio_blocks_only_still_matching_passage(client, monkeypatch):
    client, module = client
    body = {'transcript':'Bring prototype. Meet later.', 'recorded_at':'2026-10-05T10:00:00+05:30'}
    item = client.post('/api/conversations',json=body).json()
    item.update(raw_transcript=body['transcript'], speech_warnings=[{'quote':'Bring prototype.', 'start':0, 'end':1, 'reason':'Uncertain'}])
    module.save(item)
    cid=item['id']
    async def fake(*args):
        quote='Bring prototype.' if 'Bring prototype.' in args[0] else 'Bring the prototype.'
        return Understanding(title='Task', recap=quote, actions=[Action(type='task', title='Bring prototype', evidence=quote)])
    monkeypatch.setattr(module,'understand',fake)
    # Editing a different sentence must not clear the uncertain passage.
    client.put(f'/api/conversations/{cid}/transcript',json={**body,'transcript':'Bring prototype. Meet tomorrow.'})
    result=client.post(f'/api/conversations/{cid}/understand').json()
    assert result['actions'][0]['status']=='needs clarification'
    # Correcting the affected phrase makes the old audio quote stale.
    client.put(f'/api/conversations/{cid}/transcript',json={**body,'transcript':'Bring the prototype. Meet tomorrow.'})
    result=client.post(f'/api/conversations/{cid}/understand').json()
    assert result['actions'][0]['status']=='ready'

def test_task_deadline_and_google_calendar_preview(client, monkeypatch):
    client, module = client
    item=client.post('/api/tasks',json={'title':'Ship demo','deadline':'2026-10-05T16:00:00+05:30','priority':'high'}).json()
    cid=item['id']; aid=item['actions'][0]['id']
    assert item['task_plans'][aid]['priority']=='high'
    assert client.put(f'/api/conversations/{cid}/actions/{aid}/plan',json={'deadline':'2026-10-05T16:00:00'}).status_code==422
    assert client.put(f'/api/conversations/{cid}/actions/{aid}/plan',json={'deadline':'','priority':'low'}).json()['task_plans'][aid]['deadline']==''
    assert client.get(f'/api/conversations/{cid}/actions/{aid}/google-calendar').status_code==422
    a=event(reminder_minutes=30);item['actions']=[a.model_dump()];module.save(item)
    from urllib.parse import urlparse,parse_qs
    result=client.get(f'/api/conversations/{cid}/actions/{a.id}/google-calendar').json()
    query=parse_qs(urlparse(result['url']).query)
    assert query['dates']==['20261006T133000Z/20261006T140000Z']
    assert query['ctz']==['Asia/Kolkata']
    assert 'Set the notification' in query['details'][0]
    item['actions'][0]['certainty']='tentative';module.save(item)
    assert client.get(f'/api/conversations/{cid}/actions/{a.id}/google-calendar').status_code==422

def test_delete_tasks_atomic_and_notifications(client):
    client, module = client
    item=client.post('/api/tasks',json={'title':'Due now','deadline':'2020-01-01T10:00:00+00:00'}).json()
    cid=item['id'];aid=item['actions'][0]['id']
    notices=client.get('/api/notifications').json()
    assert any(n['aid']==aid and n['kind']=='deadline' for n in notices)
    bad=client.post('/api/tasks/delete',json={'targets':[{'cid':cid,'aid':aid},{'cid':cid,'aid':'missing'}]})
    assert bad.status_code==409
    assert client.get('/api/conversations/'+cid).json()['actions']
    result=client.post('/api/tasks/delete',json={'targets':[{'cid':cid,'aid':aid}]})
    assert result.json()['deleted']==1
    remaining=client.get('/api/conversations/'+cid).json()
    assert not remaining['actions'] and remaining['transcript']=='Due now'
    assert not client.get('/api/notifications').json()


def test_completed_and_uncertain_tasks_do_not_notify(client):
    client,module=client
    item=client.post('/api/tasks',json={'title':'Done','deadline':'2020-01-01T10:00:00+00:00'}).json()
    item['actions'][0]['status']='completed';module.save(item)
    assert not client.get('/api/notifications').json()
    item['actions'][0]['status']='needs clarification';module.save(item)
    assert not client.get('/api/notifications').json()

def test_delete_history_removes_audio_and_all_conversation_data(client):
    client,module=client
    item=client.post('/api/tasks',json={'title':'History deletion fixture'}).json()
    cid=item['id']
    path=module.DATA/(cid+'.wav');path.write_bytes(b'test audio')
    item['audio']=path.name;item['analysis_history']=[{'recap':'old'}];module.save(item)
    module.jobs.add(cid)
    assert client.delete('/api/conversations/'+cid).status_code==409
    assert path.exists()
    module.jobs.remove(cid)
    assert client.delete('/api/conversations/'+cid).status_code==200
    assert not path.exists()
    assert client.get('/api/conversations/'+cid).status_code==404
    assert not client.get('/api/conversations').json()
