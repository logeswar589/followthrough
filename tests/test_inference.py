import asyncio
import json
import pytest
from app import inference

def test_recording_timezone_anchor_and_evidence(monkeypatch):
    monkeypatch.setattr(inference,'config',lambda:('ollama','gemma4:e2b'))
    async def generate(prompt, schema):
        if schema['title'] == 'RecapReview':
            return json.dumps({'recap':'Bring the prototype.', 'detected_languages':['English'], 'language_issues':[]})
        assert schema['title']=='Extraction'
        assert '"recording_local_date": "2025-01-03"' in prompt
        assert '"tomorrow_date": "2025-01-04"' in prompt
        return json.dumps({'title':'Task','recap':'Bring the prototype.','actions':[{'type':'task','title':'Bring prototype','evidence':'Bring the prototype.'}]})
    monkeypatch.setattr(inference,'generate',generate)
    result=asyncio.run(inference.understand('Bring the prototype.','2025-01-02T23:30:00+00:00','Asia/Kolkata','casual'))
    assert result.actions[0].status=='ready'

@pytest.mark.parametrize('raw', ['Not JSON', '{"title":"Oops","recap":"","actions":[{"type":"purchase","title":"Buy now","evidence":"Maybe buy"}]}', '{"title":"Oops","recap":"","actions":[{"type":"task","title":"Invite","evidence":"Made-up quote"}]}'])
def test_malformed_unsupported_or_invented_model_output_is_rejected(monkeypatch,raw):
    monkeypatch.setattr(inference,'config',lambda:('ollama','gemma4:e2b'))
    async def generate(*args):
        return raw
    monkeypatch.setattr(inference,'generate',generate)
    with pytest.raises(ValueError,match='invalid or unsupported'):
        asyncio.run(inference.understand('Maybe buy','2026-10-05T09:00:00+05:30','Asia/Kolkata','casual'))

def test_local_context_limit_is_explicit(monkeypatch):
    monkeypatch.setattr(inference,'config',lambda:('ollama','gemma4:e2b'))
    with pytest.raises(ValueError,match='context window'):
        asyncio.run(inference.understand('x'*12001,'2026-10-05T09:00:00+05:30','Asia/Kolkata','casual'))
