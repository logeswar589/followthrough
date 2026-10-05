# MLH submission notes

Based on the saved Hacktoberfest Hack Day Chennai x Android Club VITC submission form supplied by the team.

- Project name: **FollowThrough**
- Link to project: https://github.com/logeswar589/followthrough
- Demo URL: Use a publicly accessible recording of the working demo. The form explicitly accepts a demo video. A localhost URL is only usable on the machine running the app.

## Technologies Used

Prioritize these tags if available in the form:

**Gemma 4, Ollama, Python, FastAPI, Whisper, faster-whisper, SQLite, JavaScript, HTML, CSS, GitHub.**

Additional implementation details, if the form allows custom tags or a longer description:

**Pydantic, Uvicorn, HTTPX, CTranslate2, PyAV, MediaRecorder API, getUserMedia, iCalendar (.ics), pytest, Playwright.**

- Gemma 4 E4B performs understanding, action extraction, and recap generation locally through Ollama.
- Whisper `large-v3-turbo`, run through faster-whisper/CTranslate2 with PyAV decoding, performs multilingual speech recognition.
- The UI uses plain JavaScript, HTML and CSS. It does not use React or Next.js.
- SQLite stores recordings' metadata, transcripts, recaps and tasks; audio files are stored separately.
- Google Calendar support opens a reviewed, prefilled event URL and exports `.ics`. It does not use OAuth or the Google Calendar API.
- Hosted Gemma through the Gemini API is implemented as an optional provider. List it as a live-demo technology only if you configure a key and successfully verify it.
- Vercel deployment was paused. Do not claim a deployed Vercel backend.
- GitHub hosts the public source; MIT licenses the app. AI model and dependency licenses remain separate.

## Challenge choices

The saved form offers **Best Use of Gemma 4** and **Best Open-Source AI Project**. Both match the implemented project: Gemma is central to its behavior, and the source is public with an MIT license. The skill-standard and model-harness requirements apply to entries presented as those categories; FollowThrough is a productivity app using an open-weight model. Final eligibility is the organizers' decision.

## Suggested description

FollowThrough turns spoken thoughts into next steps you can review and act on. Record or upload a voice note, review its multilingual Whisper transcript, and let Gemma 4 extract notes, decisions, tasks and calendar proposals with exact supporting quotations. It handles explicit corrections and preserves uncertainty, conditions and negation instead of treating every sentence as a commitment. A task inbox adds completion controls, deadlines and reminders while the app is open. Calendar actions are reviewed before opening Google Calendar or exporting an .ics file. Original audio, transcripts, recaps and actions stay together in local storage. The prototype uses local Ollama inference, optional hosted Gemma support, and an MIT-licensed Python/FastAPI and JavaScript codebase.
