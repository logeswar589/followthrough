"""Finish live smoke/evaluation once a previously started local pull completes."""
import json
from pathlib import Path
import subprocess
import sys
import time
import httpx

deadline=time.monotonic()+4*3600
print('Waiting for the local gemma4:e2b model download; no fallback.',flush=True)
while time.monotonic()<deadline:
    try:
        models=httpx.get('http://127.0.0.1:11434/api/tags',timeout=5).json().get('models',[])
        if any(model['name']=='gemma4:e2b' for model in models):
            break
    except httpx.HTTPError:
        pass
    time.sleep(15)
else:
    raise SystemExit('Model did not finish downloading within four hours.')
print('Model downloaded. Running real audio pipeline.',flush=True)
result=subprocess.run([sys.executable,'scripts/smoke.py','artifacts/synthetic-demo.wav'])
if result.returncode:
    raise SystemExit(result.returncode)
print('Audio pipeline passed. Running live semantic regressions.',flush=True)
raise SystemExit(subprocess.run([sys.executable,'-m','scripts.evaluate']).returncode)
