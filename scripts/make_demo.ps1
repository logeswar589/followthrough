# Generate a clearly synthetic test recording using Windows' installed TTS voice.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force artifacts | Out-Null
Add-Type -AssemblyName System.Speech
$demoSynth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $demoSynth.SetOutputToWaveFile((Join-Path (Get-Location) 'artifacts\synthetic-demo.wav'))
    $demoSynth.Speak('Meet tomorrow at six. Actually seven P M, in the library, for thirty minutes. Remind me half an hour before. Bring the prototype. We need an HDMI adapter under eight hundred rupees. Wait until we confirm the laptop port. Maybe ask Rahul to join and send him a recap.')
} finally { $demoSynth.Dispose() }
Write-Output 'Created artifacts/synthetic-demo.wav. This is generated test speech, not a real person recording.'
