"""Read-only setup diagnostics. Never prints credentials or transcript data."""
import importlib.metadata
import json
import sys
from pathlib import Path
import httpx

def main():
    print('Python:',sys.version.split()[0])
    for package in ['fastapi','faster-whisper','av','pydantic']:
        try:
            print(package+':',importlib.metadata.version(package))
        except importlib.metadata.PackageNotFoundError:
            print(package+': not installed')
    print('.env:', 'present' if Path('.env').exists() else 'missing; copy .env.example')
    try:
        health=httpx.get('http://127.0.0.1:8000/api/health',timeout=5)
        health.raise_for_status()
        print('App:',json.dumps(health.json()))
    except httpx.HTTPError:
        print('App: not responding at http://127.0.0.1:8000')
    try:
        result=httpx.get('http://127.0.0.1:11434/api/tags',timeout=5)
        result.raise_for_status()
        names=[m['name'] for m in result.json().get('models',[])]
        print('Ollama models:',', '.join(names) or '(none installed yet)')
    except httpx.HTTPError:
        print('Ollama: not responding at http://127.0.0.1:11434')

if __name__=='__main__':
    main()
