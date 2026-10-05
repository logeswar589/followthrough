# Hack Day demo

## 75–90 second pitch

“Most productivity apps start when you type a task. Real commitments start in conversation. FollowThrough turns what you say into the next steps you would otherwise forget.

Here’s a quick voice note: meet tomorrow at six—actually seven PM—in the library, bring the prototype, and find an HDMI adapter under eight hundred rupees. But wait until we confirm the port. Maybe invite Rahul.

Whisper transcribes locally. I can correct names before Gemma 4 interprets it. Notice the correction to seven, the shopping action waiting for compatibility, and Rahul staying tentative. Every card points back to the exact words that support it.

I review the meeting, confirm its duration, and download a calendar file. The prototype becomes a saved task. The recap keeps the conditions and can stay casual or become professional.

The original recording, transcript and next steps stay together. This is a working local-first, open-source prototype: no automatic messages, purchases or invented product prices. FollowThrough makes the gap between saying and doing a little smaller.”

## Demonstration sequence

The local `artifacts/followthrough-walkthrough.webm` is a 34-second silent walkthrough of verified output from labelled synthetic audio. Use it as a backup or add your own narration; the pitch below is intended for a live presentation. To regenerate after `scripts/smoke.py`, run `node scripts/record-demo.cjs` with Playwright and Edge available. Artifacts are ignored by Git; intentionally select and attach the final video when preparing the submission.

1. Test the model connection before judging. Keep Ollama warmed up.
2. Record a 15–25 second team-consented voice note, or upload a clearly labelled synthetic fixture. Do not represent generated sample audio as live microphone input.
3. Show the original audio and editable transcript. Correct any transcription mistakes openly.
4. Use a recording date of 5 October 2026, Asia/Kolkata. Ask for a meeting tomorrow at seven PM for 30 minutes. Verify 6 October, 19:00 IST.
5. Understand with Gemma. Show exact evidence, shopping conditions and tentative invitation.
6. Open the event review and export `.ics`. Say “downloaded for import”, not “added to Google Calendar”.
7. Mark the prototype task done. Edit/copy the recap. Reload and show persistence.
8. If time permits, change the original transcript to “seven” without AM/PM. Rerun and demonstrate a clarification question.

## Remaining-day plan (Asia/Kolkata)

Environment check began around 10:00 AM on 5 October, leaving seven hours until the 5 PM hard submission end. Target **4 PM** to avoid last-minute submission risk.

| Window | Deliverable |
|---|---|
| 10:00–11:00 | Model access, local model download, audio-to-action vertical slice |
| 11:00–12:30 | Inbox, editing, persistence, calendar export |
| 12:30–2:00 | Real team recordings; corrections, uncertainty, mixed-language evaluation |
| 2:00–3:15 | Fix failures; finish responsive polish; freeze features |
| 3:15–4:00 | Reserved 45 min: tests, README, license, GitHub, demo recording and submission |
| 4:00–5:00 | Submission buffer; keep known-good version runnable |
| 5:15 | Judging begins |

Stretch features should wait until the core works reliably. Voice cloning is the first feature to cut, then live shopping, then direct calendar integration.
