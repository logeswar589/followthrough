"""Server-only model preferences. Credentials never appear in public settings."""
import json
import os
from pathlib import Path

SETTINGS_PATH = Path(os.getenv('FOLLOWTHROUGH_DATA', Path(__file__).resolve().parent.parent / 'data')) / 'model-settings.json'
LOCAL_MODELS = [
    {'id': 'gemma4:e2b', 'label': 'Gemma 4 E2B', 'hint': 'Lightest · about 4.6 GB download'},
    {'id': 'gemma4:e4b', 'label': 'Gemma 4 E4B', 'hint': 'Recommended · about 6.6 GB download; may use CPU alongside a 6 GB GPU'},
    {'id': 'gemma4:12b', 'label': 'Gemma 4 12B', 'hint': 'Larger · about 8 GB download; more memory needed'},
    {'id': 'gemma4:26b', 'label': 'Gemma 4 26B', 'hint': 'High memory · about 17 GB download; unsuitable for most 16 GB laptops'},
    {'id': 'gemma4:31b', 'label': 'Gemma 4 31B', 'hint': 'High memory · about 20 GB download; use a powerful workstation'},
]
CLOUD_MODELS = [
    {'id': 'gemma-4-26b-a4b-it', 'label': 'Gemma 4 26B A4B'},
    {'id': 'gemma-4-31b-it', 'label': 'Gemma 4 31B'},
]

def read_settings():
    if not SETTINGS_PATH.exists():
        return {}
    return json.loads(SETTINGS_PATH.read_text(encoding='utf-8'))

def api_key():
    prefs = read_settings()
    return prefs.get('api_key', os.getenv('GEMINI_API_KEY', ''))

def save_settings(provider, model, key=None, clear_key=False):
    prefs = read_settings()
    prefs.update(provider=provider, model=model)
    if clear_key:
        prefs['api_key'] = ''
    elif key:
        prefs['api_key'] = key
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = SETTINGS_PATH.with_suffix('.tmp')
    temporary.write_text(json.dumps(prefs), encoding='utf-8')
    temporary.replace(SETTINGS_PATH)
