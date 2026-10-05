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

@pytest.mark.parametrize('scenario', ['missing', 'ready', 'offline', 'removed'])
def test_local_model_readiness_before_inference(monkeypatch, scenario):
    import httpx
    monkeypatch.setattr(inference, 'config', lambda: ('ollama', 'gemma4:e4b'))
    calls = []
    def runtime(request):
        calls.append(request.url.path)
        if request.url.path == '/api/tags':
            if scenario == 'offline':
                raise httpx.ConnectError('offline', request=request)
            return httpx.Response(200, json={'models': [] if scenario == 'missing' else [{'name':'gemma4:e4b'}]})
        if scenario == 'removed':
            return httpx.Response(404, json={'error':'model not found'})
        body=json.loads(request.content)
        assert body['model']=='gemma4:e4b'
        return httpx.Response(200, json={'message':{'content':'{"ok":true}'}})
    original_client = httpx.AsyncClient
    monkeypatch.setattr(inference.httpx, 'AsyncClient', lambda **kwargs: original_client(transport=httpx.MockTransport(runtime), **kwargs))
    if scenario == 'ready':
        assert json.loads(asyncio.run(inference.generate('test')))['ok']
        assert calls == ['/api/tags','/api/chat']
    else:
        message = {'missing':'not installed yet','offline':'not reachable','removed':'not available in Ollama'}[scenario]
        with pytest.raises(ValueError, match=message):
            asyncio.run(inference.generate('test'))
        assert calls == (['/api/tags','/api/chat'] if scenario == 'removed' else ['/api/tags'])
