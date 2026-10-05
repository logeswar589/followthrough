$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force artifacts | Out-Null
$testOutput = 'artifacts/pytest-' + [guid]::NewGuid().ToString('N')
& '.\.venv\Scripts\python.exe' -m pytest -q --basetemp $testOutput
exit $LASTEXITCODE
