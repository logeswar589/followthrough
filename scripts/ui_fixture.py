"""Isolated manual UI test server, never used by the real app.
Run: python -m scripts.ui_fixture; open localhost:8001.
The seeded data is explicitly labelled and no model inference is claimed.
"""
import os
from pathlib import Path
from uuid import uuid4
os.environ['FOLLOWTHROUGH_DATA'] = str(Path('artifacts/ui-test-data').resolve())
from app.main import app, save
from app.models import Action
import uvicorn

text = 'Meet tomorrow at seven PM in the library for 30 minutes. Remind me half an hour before. Bring the prototype. We need an HDMI adapter under 800 rupees. Wait until we confirm the laptop port. Maybe invite Rahul.'
actions = [
    Action(id='event-fixture',type='event',title='Prototype meetup',evidence='Meet tomorrow at seven PM in the library for 30 minutes. Remind me half an hour before.',date='2026-10-06',time='19:00',timezone='Asia/Kolkata',duration_minutes=30,reminder_minutes=30,location='Library'),
    Action(id='task-fixture',type='task',title='Bring the prototype',evidence='Bring the prototype.'),
    Action(id='shopping-fixture',type='shopping',title='Find an HDMI adapter',evidence='We need an HDMI adapter under 800 rupees. Wait until we confirm the laptop port.',product='HDMI adapter',budget_inr=800,certainty='conditional',status='needs clarification',missing=['Which laptop port should the adapter support?']),
    Action(id='draft-fixture',type='draft',title='Maybe invite Rahul',evidence='Maybe invite Rahul.',certainty='tentative',status='needs clarification',missing=['Do you want to invite Rahul?'],details='Possible invitation, not sent.'),
]
save({'id':'ui-fixture','created_at':'2026-10-05T09:45:00+05:30','recorded_at':'2026-10-05T09:45:00+05:30','timezone':'Asia/Kolkata','style':'casual','source':'sample','title':'UI test fixture — no model inference','transcript':text,'recap':'SAMPLE FIXTURE: Meet tomorrow at 7 PM for 30 minutes. Bring the prototype. Adapter search waits on laptop port confirmation. Rahul is a possible invitee.','actions':[a.model_dump() for a in actions],'segments':[],'audio':None,'model':'UI fixture (no inference)'})

if __name__=='__main__':
    uvicorn.run(app,host='127.0.0.1',port=8001)
