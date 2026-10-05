"""Run live Gemma regressions. Failures are printed and saved, never replaced with fixtures.
Run from project root: python -m scripts.evaluate
"""
import asyncio
import json
from pathlib import Path
import time
from app.inference import understand

CASES = [
    ('correction', 'Meet tomorrow at six PM, actually seven PM, in the library for 30 minutes. Remind me half an hour before. Bring the prototype.', '2026-10-05T09:45:00+05:30'),
    ('uncertainty', 'We need an HDMI adapter under 800 rupees. Do not buy it yet. Wait until we confirm the laptop port. Maybe invite Rahul and send him a recap.', '2026-10-05T09:45:00+05:30'),
    ('missing_time', 'Meet tomorrow in the library. Bring the prototype.', '2026-10-05T09:45:00+05:30'),
    ('ambiguous_hour', 'Meet tomorrow at six, actually seven, in the library.', '2026-10-05T09:45:00+05:30'),
    ('old_recording', 'Meet tomorrow at 7 PM for 30 minutes.', '2025-01-02T09:45:00+05:30'),
    ('asr_uncertainty', 'May be ask Rahul to join. Do not send the recap yet.', '2026-10-05T09:45:00+05:30'),
]

async def main():
    results=[]
    for name,text,recorded in CASES:
        start=time.monotonic()
        output=None
        try:
            output=await understand(text,recorded,'Asia/Kolkata','casual')
            actions=output.actions
            events=[a for a in actions if a.type=='event']
            if name=='correction':
                assert events and events[0].time=='19:00' and events[0].date=='2026-10-06', 'Correction or date lost'
                assert events[0].reminder_minutes==30, 'Reminder lost'
                assert any(a.type=='task' and 'prototype' in a.title.lower() for a in actions), 'Checklist lost'
            if name=='uncertainty':
                shopping=[a for a in actions if a.type=='shopping']
                assert shopping and shopping[0].budget_inr==800, 'Budget lost'
                assert shopping[0].status=='needs clarification', 'Shopping condition lost'
                assert not any(a.status=='ready' and 'rahul' in (a.title+a.details).lower() for a in actions), 'Maybe became confirmed'
            if name in ('missing_time','ambiguous_hour'):
                assert events and not events[0].time and events[0].status=='needs clarification', 'Missing time guessed'
            if name=='old_recording':
                assert events and events[0].date=='2025-01-03', 'Used today instead of recording date'
            if name=='asr_uncertainty':
                assert actions and not any(a.status=='ready' for a in actions), 'ASR may be/negation became a confirmed action'
            results.append({'case':name,'passed':True,'seconds':round(time.monotonic()-start,1),'output':output.model_dump()})
        except Exception as exc:
            results.append({'case':name,'passed':False,'seconds':round(time.monotonic()-start,1),'error':str(exc),
                'output':output.model_dump() if output is not None else None})
        print(json.dumps(results[-1],ensure_ascii=False),flush=True)
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/live-evaluation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    return all(r['passed'] for r in results)

if __name__=='__main__':
    raise SystemExit(0 if asyncio.run(main()) else 1)
