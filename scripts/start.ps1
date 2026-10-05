$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (!(Test-Path '.venv\Scripts\python.exe')) { throw 'Create .venv and install requirements.txt first. See README.md.' }
& '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000
