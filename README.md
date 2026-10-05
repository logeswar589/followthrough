# FollowThrough ↗

**Turn what you say into the next steps you would otherwise forget.**

A local-first voice inbox built for Android Club VIT Chennai’s Hacktoberfest 2026 Hack Day. Record or upload a thought, review the transcript, and let **Gemma 4** propose evidence-backed actions. You decide what happens next.

## Run locally

Requires Python 3.12+, Ollama, and a modern browser. Allow roughly 12–15 GB free disk space for the Windows runtime, installer, dependencies and model files. Local Gemma performance depends on available RAM/VRAM. The development machine has 16 GB RAM and a 6 GB RTX 3050.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `GEMMA_PROVIDER=ollama` in `.env`. Then:

```powershell
ollama pull gemma4:e4b
# Start Ollama if it is not already running:
ollama serve
```

In another terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open [localhost:8000](http://127.0.0.1:8000). Use **Test connection** to run an actual model request. The **Models** popup also offers connection testing on desktop and mobile. First transcription downloads Whisper `large-v3-turbo` (~1.6 GB). CPU int8 keeps speech recognition from competing with Gemma for the 6 GB GPU. It is a much larger multilingual model than the original `base` configuration. Automatic language detection is enabled for each decoding window, with transcription in the source language instead of forced English translation. This supports language switches but does not guarantee reliable word-by-word code-switching. Speech settings are reloaded when transcription starts; no silent smaller-model fallback is used.

`requirements.lock.txt` records the exact tested dependency set. Install it in place of `requirements.txt` for reproducibility. PyAV is constrained to 16.x because the tested 19.x release removed a decoder argument required by faster-whisper.

No precomputed extraction is used. The example button supplies sample text and still requires live inference. Synthetic integration recordings are labelled. The UI reports failures instead of silently changing models.

### Optional hosted Gemma

Set in `.env`:

```dotenv
GEMMA_PROVIDER=google
GEMINI_API_KEY=your_private_key
GEMMA_MODEL=gemma-4-26b-a4b-it
```

This uses **Gemma**, hosted through the Gemini API; it does not substitute a Gemini model. Credentials stay on the server. The provider is reread on each inference request. Refresh the UI after changing it. Transcript text is sent to Google in this mode; original audio stays local. Access/quota must be verified with your key.

## What the MVP does

- Delete individual task cards or all listed tasks across filters, with confirmation. Recordings, transcripts, recaps and historical analyses remain; re-extraction may propose tasks again. Demo examples are excluded from bulk deletion unless “Include demo examples” is checked.
- Clearly labelled Google Calendar buttons for ready events; incomplete events offer “Review for Calendar.” Ordinary task cards are not calendar events.


- Task-first home screen with conversation history in the left sidebar, quick task entry, Remaining/Today/Overdue/Completed views, and hover/focus evidence previews.
- Explicit task deadlines and priorities persisted separately from model proposals. Deadline countdowns use the device timezone and update while the page is open. A notification tray checks ready tasks and event reminder times every 10 seconds. Optional desktop alerts require browser permission; they cannot run after the tab closes or reliably wake a sleeping device. Re-extraction creates new proposals, so review and reassign their deadlines.
- Reviewed Google Calendar handoff for ready events. The preview opens a prefilled Google Calendar event; you press Save there. No OAuth account connection, background sync, or automatic event insertion is implemented. Google notifications must be checked there; `.ics` still includes the requested alarm.

- Explicit browser microphone start/stop and consent acknowledgement; audio upload up to 30 MB / 10 minutes.
- Real local faster-whisper transcription with original-audio playback and segment seeking.
- Editable transcript, recording date, timezone, recap tone and output language. Auto keeps the source language mix; named languages request a translated recap.
- Original machine transcript retained separately; word confidence flags and replayable uncertain passages help review mishearings.
- Gemma performs action extraction and a separate focused recap/language review. Suspected wording issues show exact quotes and tentative suggestions; affected actions need review.
- Gemma extraction into a finite Pydantic schema: events, tasks, decisions, shopping, drafts and questions.
- Exact supporting transcript quotations, confirmation/condition tracking, editable review cards.
- SQLite persistence across reloads: recordings, transcript, recap and actions stay together.
- Calendar preview/edit and `.ics` export with explicit date/timezone/duration and optional calendar alarm.
- Saved tasks, manual completion/dismissal, editable/copyable/downloadable recap.
- Prepared shopping search links after clarification. No fabricated product listings or prices.
- Conversation search and mobile-friendly layout.

The app is a single-user localhost demo, **not a multi-user hosted service**. It binds to loopback and rejects foreign hosts/origins. Do not expose it publicly without authentication, storage controls and deployment hardening.

Run `python scripts/doctor.py` inside the virtual environment for setup diagnostics without exposing credentials or recordings. The UI shows when Ollama is running but its model is not installed yet.

## Model access, licensing and hosting

Verified against official documentation on **5 October 2026**:

| Option | Identifier | Input / output | Notes |
|---|---|---|---|
| Gemini API | `gemma-4-26b-a4b-it`, `gemma-4-31b-it` | Text/image → text | API key required; account access must be tested |
| Ollama | `gemma4:e2b`, `gemma4:e4b`, `gemma4:12b`, `gemma4:26b`, `gemma4:31b` | Runtime-dependent; this app uses text → text | Explicit local model, no API credential |
| Self-hosted weights | Google Gemma 4 family | E2B/E4B/12B support audio in the model family; larger variants text/image | Hugging Face/Kaggle downloads; Transformers and other supported runtimes; Vertex AI is another deployment route |

Gemma 4 is listed under **Apache 2.0**. This application is **MIT**. Model/dependency licenses remain their own; no model weights are committed. faster-whisper is MIT and implements OpenAI Whisper ASR. The app deliberately separates ASR from understanding: model-family audio support does not imply audio support in every hosting API.

Sources:
- [Google: Gemma through the Gemini API](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api)
- [Google: Gemma 4 model card and license](https://ai.google.dev/gemma/docs/core/model_card_4)
- [Google: Gemma hosting/getting started](https://ai.google.dev/gemma/docs/get_started)
- [Ollama: Gemma 4 model identifiers](https://ollama.com/library/gemma4/tags)
- [faster-whisper: installation, CPU and GPU requirements](https://github.com/SYSTRAN/faster-whisper)

## Architecture and action safety

```text
Browser MediaRecorder / upload
        ↓ original audio saved locally
FastAPI → faster-whisper → editable transcript + segment timestamps
        ↓ recording time + timezone + style
Gemma 4 → JSON schema validation → exact evidence validation
        ↓
SQLite conversation inbox → user review → .ics / saved tasks / prepared search
```

`app/inference.py` owns providers and prompting. `app/models.py` validates proposals. `app/calendar.py` exports escaped, folded RFC-style iCalendar with UTC timestamps. `app/main.py` owns storage and finite handlers. `static/` contains the dependency-free frontend.

Model output is untrusted. Arbitrary model tools/code are never executed. Invalid schemas and non-verbatim evidence fail closed. New model proposals cannot self-mark completed. Uncertainty or missing required event fields block export. Transcript/context edits invalidate old actions while retaining a previous-analysis snapshot in storage. A human can explicitly confirm a proposal through review.

Previous analyses are available in a read-only history beneath the conversation. Unsaved transcript/recap edits warn before switching views. Regeneration creates fresh proposals and archives the old review state.

Semantic correctness still requires review: a valid quotation alone does not prove every extracted field. Negation, mixed-language phrasing and small-model inference need real-world evaluation.

Conservative English evidence checks additionally clear unsupported AM/PM, carry “maybe” across joined clauses, and block shopping when the following sentence says to wait. They may over-block; explicit human review can confirm the intended values. They are not a multilingual semantic guarantee. See [validation results](docs/VALIDATION.md) for measured live behavior.

## Testing

```powershell
.\scripts\test.ps1
```

Tests cover timezone conversion, alarms, escaping/line folding, missing fields, uncertain actions, fabricated evidence, old recording context, persistence, stale-action invalidation, failed extraction, invalid uploads, origin checks, and DST ambiguity. Test model responses are mocked only in isolated unit tests; the app has no mock inference mode.

For real speech checks on Windows, run `scripts/make_demo.ps1`, set `RUN_ASR_TESTS=1`, then run the tests. This tests synthetic English and silence; it does not establish mixed-language or Indian-accent accuracy. `python -m scripts.evaluate` runs live Gemma regressions for correction, uncertainty, missing time and old recording dates, saving actual results in `artifacts/`.

Optional browser regression: install Playwright in your development environment, start `python -m scripts.ui_fixture` in a separate terminal, then run `node scripts/browser-test.cjs`. It uses a separate database on port 8001, explicitly labelled sample action data, and Edge with synthetic microphone input. It checks the actual recording flow, calendar download, recap persistence, browser errors and mobile overflow. It does not mock or validate Gemma inference; use the live evaluation for that. The main app requires no Node packages.

For an actual audio → Whisper → Gemma integration check, start both services and run:

```powershell
.\.venv\Scripts\python.exe scripts/smoke.py path\to\synthetic-or-consented.wav
```

This creates a **synthetic-labelled** conversation and writes the actual result to ignored `artifacts/live-smoke.json`. Use a synthetic fixture for this script; ordinary team recordings should be uploaded through the UI.

## Multilingual understanding and wording review

The local Gemma provider now enables thinking (`OLLAMA_THINK=true`) to improve the tested multilingual cases, at the cost of latency. Set it to `false` only after checking the quality trade-off for your input. Understanding uses two focused Gemma calls: action extraction, then recap and language review. It does not replace Gemma with a different model.

Transcription uses `task=transcribe`, automatic language selection and multilingual decoding. It saves the original ASR text, word timestamps/probabilities and primary-language estimate. Word probability below 0.55 or segment average log probability below -0.8 triggers a replay flag. These are heuristics, not calibrated error probabilities. If an action overlaps a flagged passage whose original wording is still present, it requires review. Editing the affected passage makes its old ASR flag stale for action gating; editing unrelated text does not clear it. The original remains available.

Gemma detects source languages from the text, checks its recap against the source, and may flag suspicious words, unresolved contradictions or translation ambiguity. It does not hear the recording in this pipeline and cannot establish that a guessed correction is true. Slang/code-switching should not be treated as errors, but false positives and missed discrepancies remain possible. A local consistency check also flags split Latin-script terms that differ by one letter from a long term elsewhere in the same transcript. Recap checks flag possible lost dates, uncertainty, waiting conditions, budgets or original scripts, then request one Gemma repair. Remaining warnings are displayed. These checks are incomplete and may over-flag translations. Suggestions never silently overwrite your transcript. Date/time and certainty guards recognize common English, Tamil/Hindi and other supported daypart expressions; unknown ambiguous wording still requires confirmation.

`python -m scripts.evaluate_languages` runs live text checks for English, Hindi, Tamil, Tanglish and a deliberately suspicious technical phrase. These are not audio-recognition benchmarks. Inspect failures and actual recaps in `artifacts/language-evaluation.json`; passing a few fixtures is not broad language support certification.

Speech sources: [Whisper large-v3-turbo model card](https://huggingface.co/openai/whisper-large-v3-turbo), [faster-whisper model mapping](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/utils.py), [multilingual decoding implementation](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py).

## Honest boundaries

- Calendar export is a file download, not an external calendar write. Alarm delivery depends on the importing calendar app.
- Task reminders are browser-based: the app and server must remain running. Background throttling, sleeping devices and browser permissions can delay or prevent desktop delivery. Old due items stay in the tray; only reminders under five minutes old trigger desktop alerts.
- Shopping links are prepared searches, not retrieved listings, quotes or purchasing.
- No messaging, autonomous purchases, live call capture, always-on listening, speaker identity inference or voice cloning.
- No claim of broad language/accent accuracy. Evaluate Indian English and your actual mixed-language recordings before judging.
- Whisper may mishear names/numbers or hallucinate on noisy audio. Review the transcript first. Segment timestamps refer to the original ASR, even after transcript edits.
- Large recordings and concurrent users are outside this local demo’s target. Model requests have timeouts; originals survive failures.
- Local data is not encrypted at rest. `data/`, `.env`, recordings, model weights and generated test artifacts stay out of Git.

## Submission

See [docs/DEMO.md](docs/DEMO.md) for the pitch, flow and remaining-day schedule. Before publishing, run tests, inspect `git status`, verify `.env`/`data` are ignored, and record a real end-to-end demo. Publish this source repository under the included MIT license; add the actual public GitHub URL to your submission. A remote repository is not created automatically.

### Model picker
Open **Models** in the workspace to select local Gemma 4 E2B, E4B (default), 12B, 26B, or 31B. Download missing models with the displayed Ollama command. Larger models need more memory.

Choose **Cloud** for hosted Gemma 4 and enter a Google AI Studio API key. Save, then test the connection. Cloud understanding sends transcripts and context to Google; speech transcription remains local. Keys are stored in plaintext in the ignored `data/model-settings.json`, never returned by settings endpoints or stored in browser storage. Blank key keeps the saved key; Remove saved key also disables the environment fallback. Preferences override `.env`; remove the settings file to return to environment configuration. Model changes are blocked during processing.

### Appearance settings
The cover and workspace default to neon green on dark black. Open **Settings** on either page to choose Neon green, Glacier (cyan), After hours (violet), Golden hour (amber), or Graphite. Light/dark mode and palette choices apply immediately and are saved in your browser.
