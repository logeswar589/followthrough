# Validation record

## Deletion and deadline notifications

- 40 core tests passed (two opt-in ASR tests skipped). New checks cover transactional deletion, recording/transcript retention, removal of deadline plans, and exclusion of completed/uncertain tasks from reminders.
- Isolated browser checks passed for visible Calendar buttons, in-app notification display, cancelled deletion, confirmed bulk deletion, notification removal and mobile overflow. No user tasks were deleted by these checks.
- Desktop OS notification delivery has not been verified on the user's browser. Permission is requested only by pressing Enable desktop alerts. In-app reminders poll every ten seconds while the page/server are running; closed tabs and sleeping devices are not supported.

## Task workspace update

- 38 core tests passed; two real ASR tests skipped for this UI/API change (the previous full run passed them).
- Browser checks verified sidebar history, manual task creation, ticking countdown, saved deadline/priority after reload, completion filtering, action review dialog, and mobile width at 390 px.
- Google Calendar handoff verified locally: server rejects incomplete/conditional events and produces UTC dates with the selected timezone. Browser preview/link inspected without opening or saving to an external calendar. Account authentication and Google Save were not exercised.
- Desktop/mobile screenshots: `artifacts/task-workspace.jpg` and `artifacts/task-workspace-mobile.jpg`.

## Multilingual upgrade — 5 October 2026

- Replaced the default Whisper base configuration with `large-v3-turbo`, CPU int8. Downloaded 1,617,884,929-byte model and verified SHA-256 against the Hugging Face LFS object ID before loading it.
- Enabled source-language transcription and per-window automatic language detection, word timestamps, confidence-based replay flags, and retained original machine transcript.
- Final combined suite: **39 passed**, including real upgraded-model speech and silence checks (41.19 seconds for the suite).
- Real synthetic-English audio pipeline passed semantic assertions: transcription **17.5 seconds**, Gemma **46.6 seconds**, with another live evaluation running concurrently. This is not an isolated latency benchmark. The recap preserved meeting correction, duration, reminder, prototype, INR 800 ceiling, port condition and tentative Rahul invitation.
- Browser verified output-language preference survives reload, suspected split-term wording appears with its suggestion, affected action is blocked pending review, and 390 px layout has no document overflow or JavaScript errors.
- Gemma uses thinking mode and separate extraction/recap passes. Optional recap repair is triggered by fidelity checks. These checks detect only specific patterns and can produce false positives or miss errors.
- Live Tamil API case preserved Tamil recap, 19:00 next-day event, budget and prohibition. A deliberately suspicious split term was flagged through within-transcript consistency checking after Gemma alone missed it.
- Final live text evaluation: **all five cases passed** (English uncertainty, Hindi, Tamil, Tanglish, suspicious wording). Assertions cover next-day evening time, budget, blocked purchasing and uncertainty; these are limited semantic checks, not a complete translation-quality score.
- New artifacts: `upgraded-test.log`, `upgraded-smoke.log`, `language-evaluation.json`, `ui-tamil-live.json`, `ui-wording-live.json`, and `language-review-*.jpg`.

This upgrade does **not** establish real Tamil/Hindi/code-switched audio accuracy. Multilingual text tests and synthetic English audio are different evidence. Original recordings and editable transcripts remain essential. Earlier base-model timings below are historical, not current performance.

Development machine: Windows, Python 3.12, 16 GB RAM, NVIDIA RTX 3050 6 GB. Local model selected: `gemma4:e2b`; optional Google provider remains available.

## Verified so far

- Final combined suite: 27 passed (25 core tests and two opt-in ASR tests loading the real model).
- Real ASR suite: synthetic English speech and three seconds of silence passed.
- The same synthetic audio encoded as WebM/Opus was transcribed correctly, exercising the browser recording format.
- Chromium/Edge with injected synthetic microphone audio: Start recording → 31 seconds → Stop → original WebM saved → real Whisper transcript passed. This does not verify the physical microphone or a real accent.
- Browser file chooser → upload → local Whisper → editable transcript worked with the generated 22-second fixture.
- Original audio playback, persisted transcript retrieval after page reload, and labelled sample/synthetic conversations inspected in browser.
- Mobile viewport checked at 390 px: document width did not exceed viewport width.
- `node --check static/app.js` passed.
- Ollama installed from the official package and detects the RTX 3050 through CUDA after restart.
- Isolated UI fixture: shopping clarification edit changed a conditional action into a prepared search only after explicit review. This fixture is labelled and runs on port 8001, with separate ignored storage; it is not model output.
- Calendar HTTP export produced `DTSTART:20261006T133000Z` (7 PM IST) and a 30-minute display alarm. Task completion persisted when fetched again.
- Browser download control produced the expected `.ics`; recap edits survived reload. Multiple conversations exposed a mobile grid sizing issue, fixed and rechecked at 390 px.
- Final automated browser regression passed all checks with no page JavaScript errors; screenshots and exported calendar are in ignored `artifacts/`.
- Transcript changes archive old analyses, including recap-only results; old actions cannot still export after invalidation.

## Live model verified — 5 October 2026

Gemma `gemma4:e2b` (Q4_K_M, Ollama 0.35.1) downloaded and ran locally on the RTX 3050. All six live regression cases passed: correction, uncertainty/budget, missing time, ambiguous AM/PM, old recording date, and ASR's “may be”. The final run took 1.0–7.0 seconds per case with the model warm.

The final audio smoke test passed semantic assertions: 19:00 on 6 October 2026, 30-minute alert, prototype task, INR 800 budget, shopping blocked on port confirmation, and a tentative Rahul action. Measured transcription: 4.4 seconds; understanding: 4.8 seconds. Input was synthetic English, not a real participant recording.

Actual model-generated cards were then checked in a browser on port 8000: shopping had no executable search link while blocked, calendar download had the correct UTC start, and mobile layout had no document overflow. Results are in `artifacts/live-smoke.json`, `artifacts/live-evaluation.json`, `artifacts/live-calendar.ics`, and the `followthrough-live*.jpg` screenshots. The UI has no mock understanding provider.

A 34-second silent walkthrough is saved as `artifacts/followthrough-walkthrough.webm`. It shows existing real Gemma output from the labelled synthetic recording, transcript, calendar download, conditional shopping, tentative invitation and recap. Video validation decoded all 844 frames at 1440 × 1000; this is a recorded UI walkthrough, not a live human microphone demonstration.

Initial live runs failed on dropped fields and ambiguity. Prompt refinements plus conservative English evidence checks fixed these evaluated cases. The checks can over-block legitimate actions; human review can resolve them. Six short cases are not a broad accuracy benchmark. Recap style and completeness still need human review, especially across mixed languages.

## Not established by these tests

- Physical microphone capture on the user's device. Test with the team's knowledge and consent.
- Indian-accent and code-switched Tamil/Hindi recordings. Synthetic English is not evidence of broad language accuracy.
- Google API access or quota for a particular account; no key supplied.
- Notification delivery, direct calendar insertion, shopping retrieval, messaging, purchases or voice cloning (not implemented).
- Public hosting or multi-user security (local demo only).

## Model picker update
- 45 automated checks passed; 2 opt-in ASR checks skipped.
- Browser checks passed for E4B default, slider selection, cloud form, key clearing, no credential in browser storage, mobile layout and dark theme. Browser save requests were mocked to preserve real settings.
- Server tests cover secret-free responses, key retention/removal, catalog validation, processing lock and cross-origin rejection.
- E4B finished downloading and passed a live `/api/model/check` request on 5 October 2026: HTTP 200, model `gemma4:e4b`, valid JSON `{"ok":true}`. The cold connection test took 50.8 seconds. This verifies inference access, not a full E4B semantic benchmark. Cloud inference requires a user-supplied API key.


## Model availability fix
- 49 automated tests passed; 2 opt-in ASR checks skipped.
- Local inference checks Ollama model installation before sending a chat request. Missing/offline runtimes and a model removed after the check produce actionable messages. No automatic model substitution.
- Browser regression verifies the model-specific notice, helpful missing-model toast, and notice disappearing once health reports the model installed.

- The neon/black palette and settings were checked in desktop and mobile browsers: five selectable schemes, light/dark switching, persistence across reloads/pages, and no page errors.
