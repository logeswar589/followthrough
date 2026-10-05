import importlib
import pytest
from fastapi.testclient import TestClient
from app import inference, model_settings

@pytest.fixture
def settings_client(tmp_path, monkeypatch):
    monkeypatch.setenv('FOLLOWTHROUGH_DATA', str(tmp_path))
    monkeypatch.setattr(model_settings, 'SETTINGS_PATH', tmp_path / 'model-settings.json')
    import app.main
    module = importlib.reload(app.main)
    return TestClient(module.app), module

def test_key_stays_server_side_and_can_be_replaced_cleared(settings_client, monkeypatch):
    client, module = settings_client
    key = 'test-private-credential'
    body = {'provider': 'google', 'model': 'gemma-4-26b-a4b-it', 'api_key': key}
    result = client.put('/api/model/settings', json=body)
    assert result.status_code == 200
    assert key not in result.text and result.json()['key_configured']
    assert model_settings.api_key() == key
    assert inference.config() == ('google', body['model'])
    result = client.get('/api/model/settings')
    assert key not in result.text and 'api_key' not in result.json()
    assert len(result.json()['local']) == 5
    body['api_key'] = ''
    client.put('/api/model/settings', json=body)
    assert model_settings.api_key() == key
    monkeypatch.setenv('GEMINI_API_KEY', 'environment-key')
    body['clear_key'] = True
    result = client.put('/api/model/settings', json=body)
    assert not result.json()['key_configured']
    assert model_settings.api_key() == ''

def test_invalid_settings_never_echo_key(settings_client):
    client, module = settings_client
    for body in [[], {'provider':'google','model':'arbitrary','api_key':'secret'}, {'provider':'google','model':'gemma-4-31b-it','api_key': {'secret':'private'}}, {'provider':'google','model':'gemma-4-31b-it','api_key':'secret with space'}]:
        result = client.put('/api/model/settings', json=body)
        assert result.status_code == 422
        assert 'secret' not in result.text and 'private' not in result.text
    assert not model_settings.SETTINGS_PATH.exists()

def test_switch_is_blocked_during_processing(settings_client):
    client, module = settings_client
    module.jobs.add('active-conversation')
    try:
        result = client.put('/api/model/settings', json={'provider':'ollama','model':'gemma4:e4b'})
        assert result.status_code == 409
        assert not model_settings.SETTINGS_PATH.exists()
    finally:
        module.jobs.clear()
    result = client.put('/api/model/settings', json={'provider':'ollama','model':'gemma4:e4b'})
    assert result.status_code == 200
    assert inference.config() == ('ollama','gemma4:e4b')

def test_cross_origin_settings_rejected(settings_client):
    client, _ = settings_client
    result = client.put('/api/model/settings', headers={'origin':'https://external.example'}, json={'provider':'ollama','model':'gemma4:e4b'})
    assert result.status_code == 403
