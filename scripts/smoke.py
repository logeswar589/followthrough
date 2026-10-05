"""Live integration smoke. The WAV is synthetic and model outputs are never mocked.
Run: python scripts/smoke.py artifacts/synthetic-demo.wav
Requires the app on localhost:8000 and its configured Gemma runtime.
"""
import json
from pathlib import Path
import sys
import time
import httpx

with httpx.Client(base_url='http://127.0.0.1:8000/api', timeout=600) as client:
    def check(response):
        response.raise_for_status()
        return response.json()
    item = check(client.post('/conversations', json={'recorded_at':'2026-10-05T09:45:00+05:30','source':'synthetic'}))
    cid=item['id']
    with Path(sys.argv[1]).open('rb') as audio:
        check(client.post(f'/conversations/{cid}/audio', files={'file':('synthetic-demo.wav',audio,'audio/wav')}))
    start=time.monotonic()
    item=check(client.post(f'/conversations/{cid}/transcribe'))
    print('TRANSCRIPTION',round(time.monotonic()-start,1),'seconds',flush=True)
    print(item['transcript'],flush=True)
    start=time.monotonic()
    item=check(client.post(f'/conversations/{cid}/understand'))
    print('GEMMA',round(time.monotonic()-start,1),'seconds',flush=True)
    events=[a for a in item['actions'] if a['type']=='event']
    shopping=[a for a in item['actions'] if a['type']=='shopping']
    assert events and events[0]['time']=='19:00', 'Corrected PM meeting time was not preserved'
    assert events[0]['date']=='2026-10-06' and events[0]['reminder_minutes']==30
    assert shopping and shopping[0]['budget_inr']==800 and shopping[0]['status']=='needs clarification', 'Shopping condition/budget lost'
    assert any('rahul' in a['title'].lower() and a['status']=='needs clarification' for a in item['actions'])
    print(json.dumps(item,ensure_ascii=False,indent=2),flush=True)
    Path('artifacts/live-smoke.json').write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding='utf-8')
