"""Wait for the authorized Ollama install, start loopback service, pull Gemma 4.
Windows development helper. Prints only coarse progress, no credentials.
"""
import os
from pathlib import Path
import subprocess
import time
import httpx

binary = Path(os.environ['LOCALAPPDATA']) / 'Programs' / 'Ollama' / 'ollama.exe'
deadline = time.monotonic() + 3600
while not binary.exists():
    if time.monotonic() > deadline:
        raise SystemExit('Ollama installation did not finish within one hour.')
    time.sleep(5)
print('Ollama binary available.', flush=True)
try:
    httpx.get('http://127.0.0.1:11434/api/version', timeout=3).raise_for_status()
except Exception:
    logs = Path('artifacts/ollama-server.log').open('ab')
    subprocess.Popen([str(binary), 'serve'], stdout=logs, stderr=logs,
                     creationflags=subprocess.CREATE_NO_WINDOW, env={**os.environ, 'OLLAMA_HOST':'127.0.0.1:11434'})
    for _ in range(30):
        try:
            httpx.get('http://127.0.0.1:11434/api/version',timeout=2).raise_for_status()
            break
        except Exception:
            time.sleep(2)
    else:
        raise SystemExit('Ollama could not start. See artifacts/ollama-server.log.')
print('Pulling gemma4:e2b from the official Ollama registry.',flush=True)
last = -1
with httpx.stream('POST','http://127.0.0.1:11434/api/pull',json={'model':'gemma4:e2b','stream':True},timeout=600) as response:
    response.raise_for_status()
    import json
    for line in response.iter_lines():
        data = json.loads(line)
        if 'error' in data:
            raise SystemExit(data['error'])
        total = data.get('total')
        percent = int(100 * data.get('completed',0) / total) if total else None
        if percent is None or percent//5 != last:
            print(data.get('status'), f'{percent}%' if percent is not None else '',flush=True)
            if percent is not None:
                last=percent//5
print('Local Gemma is ready for inference.',flush=True)
