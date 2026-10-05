import asyncio
import json
import os
import sqlite3
import httpx
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal
from pydantic import field_validator
from urllib.parse import urlencode
from .models import Action, ConversationInput, validate_understanding, Understanding
from .inference import config, generate, understand, transcribe
from .model_settings import LOCAL_MODELS, CLOUD_MODELS, api_key, save_settings
from .calendar import calendar_export
from .quality import recap_checks

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.getenv('FOLLOWTHROUGH_DATA', ROOT / 'data'))
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / 'conversations.sqlite3'
with sqlite3.connect(DB) as conn:
    conn.execute('CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
app = FastAPI(title='FollowThrough', docs_url='/api/docs')
jobs = set()

def archive_analysis(item):
    if item.get('actions') or item.get('recap'):
        history = item.setdefault('analysis_history', [])
        history.append({'saved_at': datetime.now(timezone.utc).isoformat(),
            'transcript': item['transcript'], 'recap': item['recap'],
            'actions': item['actions'], 'model': item.get('model'),
            'language_issues': item.get('language_issues', []), 'output_language': item.get('output_language', 'original')})

@app.middleware('http')
async def local_only(request: Request, call_next):
    # Local single-user app: reject browser cross-origin mutations and DNS rebinding.
    if request.url.hostname not in ('localhost', '127.0.0.1', 'testserver'):
        return JSONResponse({'detail': 'Local access only'}, status_code=403)
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        return JSONResponse({'detail': 'Cross-origin requests are not allowed'}, status_code=403)
    return await call_next(request)

def read(cid):
    with sqlite3.connect(DB) as conn:
        row = conn.execute('SELECT body FROM conversations WHERE id=?', (cid,)).fetchone()
    if not row:
        raise HTTPException(404, 'Conversation not found')
    return json.loads(row[0])

def save(item):
    with sqlite3.connect(DB) as conn:
        conn.execute('INSERT OR REPLACE INTO conversations VALUES (?,?)', (item['id'], json.dumps(item)))
    return item

def idle(cid):
    if cid in jobs:
        raise HTTPException(409, 'This conversation is processing. Please wait.')

@app.exception_handler(ValueError)
async def value_error(request, exc):
    return JSONResponse({'detail': str(exc)}, status_code=422)

@app.get('/api/health')
async def health():
    provider, model = config()
    configured = provider == 'ollama' or bool(api_key())
    state = 'key_configured' if configured else 'key_missing'
    if provider == 'ollama':
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get(os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/') + '/api/tags')
                response.raise_for_status()
                state = 'available' if any(m.get('name') == model for m in response.json().get('models', [])) else 'model_missing'
        except Exception:
            state = 'offline'
    return {'provider': provider, 'model': model, 'configured': configured, 'state': state, 'speech': os.getenv('WHISPER_MODEL', 'large-v3-turbo')}

@app.post('/api/model/check')
async def check():
    check_id = 'model-check-' + str(uuid4())
    jobs.add(check_id)
    try:
        result = await generate('Reply with a JSON object only: {"ok":true}')
        return {'ok': True, 'model': config()[1], 'response': result[:200]}
    except Exception as exc:
        raise HTTPException(503, str(exc) if isinstance(exc, ValueError) else 'Cannot reach the configured Gemma runtime. Start Ollama and pull the model, or check your API connection.')

    finally:
        jobs.discard(check_id)

@app.get('/api/model/settings')
async def model_settings():
    provider, model = config()
    installed = []
    online = False
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/') + '/api/tags')
            response.raise_for_status()
            installed = [m.get('name') for m in response.json().get('models', [])]
            online = True
    except Exception:
        pass
    return {'provider': provider, 'model': model, 'key_configured': bool(api_key()),
            'local': [{**m, 'installed': m['id'] in installed} for m in LOCAL_MODELS],
            'cloud': CLOUD_MODELS, 'ollama_online': online}

@app.put('/api/model/settings')
async def update_model_settings(request: Request):
    # Parse manually so validation responses can never echo a submitted credential.
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(422, 'Invalid model settings.')
    if not isinstance(body, dict):
        raise HTTPException(422, 'Invalid model settings.')
    provider, model = body.get('provider'), body.get('model')
    key, clear = body.get('api_key'), body.get('clear_key', False)
    catalog = LOCAL_MODELS if provider == 'ollama' else CLOUD_MODELS
    if provider not in ('ollama', 'google') or model not in [m['id'] for m in catalog]:
        raise HTTPException(422, 'Choose a model from the Gemma catalog.')
    if (key is not None and (not isinstance(key, str) or len(key) > 512 or any(c.isspace() for c in key))) or not isinstance(clear, bool):
        raise HTTPException(422, 'Invalid API key or settings.')
    if clear and key:
        raise HTTPException(422, 'Choose either a new key or remove saved key.')
    if jobs:
        raise HTTPException(409, 'Wait for current processing to finish before changing models.')
    save_settings(provider, model, key, clear)
    return {'provider': provider, 'model': model, 'key_configured': bool(api_key())}

@app.get('/api/conversations')
def conversations():
    with sqlite3.connect(DB) as conn:
        items = [json.loads(row[0]) for row in conn.execute('SELECT body FROM conversations')]
    return sorted(items, key=lambda item: item['created_at'], reverse=True)

class CreateInput(ConversationInput):
    source: Literal['live', 'sample', 'synthetic'] = 'live'

@app.post('/api/conversations')
def create(body: CreateInput):
    title = body.transcript.strip()[:65] or 'Untitled thought'
    return save(dict(id=str(uuid4()), created_at=datetime.now(timezone.utc).isoformat(), title=title, recap='', actions=[], segments=[], audio=None, **body.model_dump()))

@app.get('/api/conversations/{cid}')
def detail(cid: str):
    return read(cid)

@app.delete('/api/conversations/{cid}')
def delete_conversation(cid: str):
    idle(cid)
    item = read(cid)
    if item.get('audio'):
        audio_path = (DATA / item['audio']).resolve()
        if audio_path.parent != DATA.resolve():
            raise HTTPException(422, 'Invalid recording path.')
        audio_path.unlink(missing_ok=True)
    with sqlite3.connect(DB) as conn:
        conn.execute('DELETE FROM conversations WHERE id=?', (cid,))
    return {'deleted': cid}

@app.put('/api/conversations/{cid}/transcript')
def update_transcript(cid: str, body: ConversationInput):
    idle(cid)
    item = read(cid)
    changed = any(item.get(key) != value for key, value in body.model_dump().items())
    if changed and (item['actions'] or item['recap']):
        # Retain prior results for audit, but never leave stale actions executable.
        item['previous_analysis'] = {'recap': item['recap'], 'actions': item['actions']}
        archive_analysis(item)
        item['actions'], item['recap'] = [], ''
    if changed:
        item['language_issues'], item['detected_languages'], item['recap_warnings'] = [], [], []
    item.update(body.model_dump())
    return save(item)

@app.post('/api/conversations/{cid}/audio')
async def upload(cid: str, file: UploadFile = File(...)):
    idle(cid)
    item = read(cid)
    if item['audio']:
        raise HTTPException(409, 'Create a new conversation for a different recording.')
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in ('.wav', '.mp3', '.m4a', '.ogg', '.webm', '.mp4', '.flac'):
        raise HTTPException(415, 'Use WAV, MP3, M4A, OGG, WebM, MP4 or FLAC audio.')
    path = DATA / (cid + suffix)
    total = 0
    try:
        with path.open('wb') as output:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > 30 * 1024 * 1024:
                    raise HTTPException(413, 'Audio must be smaller than 30 MB.')
                output.write(chunk)
        if total == 0:
            raise HTTPException(422, 'The uploaded recording is empty.')
    except Exception:
        path.unlink(missing_ok=True)
        raise
    item['audio'] = path.name
    item['title'] = Path(file.filename or 'Voice note').stem[:65] or 'Voice note'
    return save(item)

@app.get('/api/conversations/{cid}/audio')
def audio(cid: str):
    item = read(cid)
    if not item['audio']:
        raise HTTPException(404, 'No audio saved')
    return FileResponse(DATA / item['audio'])

@app.post('/api/conversations/{cid}/transcribe')
async def speech(cid: str):
    idle(cid)
    item = read(cid)
    if not item['audio']:
        raise HTTPException(422, 'Upload a recording first')
    jobs.add(cid)
    try:
        result = await asyncio.to_thread(transcribe, DATA / item['audio'])
        archive_analysis(item)
        item.update(result)
        item['actions'], item['recap'] = [], ''
        item['language_issues'], item['detected_languages'], item['recap_warnings'] = [], [], []
        return save(item)
    except ValueError:
        raise
    except Exception as exc:
        raise HTTPException(503, 'Transcription failed. Check the speech model download and audio format; your recording is saved.') from exc
    finally:
        jobs.discard(cid)

@app.post('/api/conversations/{cid}/understand')
async def extract(cid: str):
    idle(cid)
    item = read(cid)
    if not item['transcript'].strip():
        raise HTTPException(422, 'Add or transcribe speech first')
    jobs.add(cid)
    try:
        speech_context = {'primary_language': item.get('language'),
            'language_probability': item.get('language_probability')}
        active_warnings = [w for w in item.get('speech_warnings', []) if w['quote'] in item['transcript']]
        speech_context['uncertain_passages'] = active_warnings[:12]
        result = await understand(item['transcript'], item['recorded_at'], item['timezone'], item['style'],
            item.get('output_language', 'original'), speech_context)
        for action in result.actions:
            action.id = str(uuid4())
            for warning in active_warnings:
                if action.evidence in warning['quote'] or warning['quote'] in action.evidence:
                    action.missing.append('Replay the uncertain audio passage and confirm its wording.')
                    action.missing = list(dict.fromkeys(action.missing))
                    action.status = 'needs clarification'
        archive_analysis(item)
        item.update(result.model_dump())
        item['model'] = config()[1]
        return save(item)
    except ValueError:
        raise
    except Exception as exc:
        raise HTTPException(503, 'Gemma could not finish. Check the runtime and retry; your recording and transcript are saved.') from exc
    finally:
        jobs.discard(cid)

class RecapEdit(BaseModel):
    recap: str = Field(max_length=12000)

@app.put('/api/conversations/{cid}/recap')
def edit_recap(cid: str, body: RecapEdit):
    idle(cid)
    item = read(cid)
    item['recap'] = body.recap
    item['recap_warnings'] = recap_checks(item['transcript'], body.recap,
        [Action.model_validate(a) for a in item['actions']], item.get('output_language', 'original'))
    return save(item)

@app.put('/api/conversations/{cid}/actions/{aid}')
def edit_action(cid: str, aid: str, body: Action):
    idle(cid)
    item = read(cid)
    index = next((i for i, action in enumerate(item['actions']) if action['id'] == aid), None)
    if index is None:
        raise HTTPException(404, 'Action not found')
    previous = item['actions'][index]
    body.evidence, body.type = previous['evidence'], previous['type']
    requested_status = body.status
    validated = validate_understanding(Understanding(title='Review', recap='', actions=[body]), item['transcript'], reviewed=True).actions[0]
    if requested_status == 'completed' and validated.status != 'ready':
        raise HTTPException(422, 'Resolve missing details before marking complete.')
    if requested_status in ('completed', 'dismissed'):
        validated.status = requested_status
    validated.id = aid
    item['actions'][index] = validated.model_dump()
    return save(item)

class TaskPlan(BaseModel):
    deadline: str = ''
    priority: Literal['low', 'normal', 'high'] = 'normal'
    @field_validator('deadline')
    @classmethod
    def valid_deadline(cls, value):
        if value and datetime.fromisoformat(value).tzinfo is None:
            raise ValueError('Deadline must include a UTC offset.')
        return value

class QuickTask(TaskPlan):
    title: str = Field(min_length=1, max_length=200)

@app.post('/api/tasks')
def quick_task(body: QuickTask):
    title = body.title.strip()
    if not title:
        raise HTTPException(422, 'Enter a task title.')
    item = create(CreateInput(transcript=title, recorded_at=datetime.now(timezone.utc).isoformat()))
    action = Action(id=str(uuid4()), type='task', title=title, evidence=title)
    item['actions'] = [action.model_dump()]
    item['task_plans'] = {action.id: TaskPlan(deadline=body.deadline, priority=body.priority).model_dump()}
    return save(item)

@app.put('/api/conversations/{cid}/actions/{aid}/plan')
def plan_task(cid: str, aid: str, body: TaskPlan):
    idle(cid)
    item = read(cid)
    if not any(a['id'] == aid for a in item['actions']):
        raise HTTPException(404, 'Action not found')
    item.setdefault('task_plans', {})[aid] = body.model_dump()
    return save(item)

@app.get('/api/conversations/{cid}/actions/{aid}/google-calendar')
def google_calendar(cid: str, aid: str):
    action = next((a for a in read(cid)['actions'] if a['id'] == aid), None)
    if not action:
        raise HTTPException(404, 'Action not found')
    event = Action.model_validate(action)
    exported = calendar_export(event)  # Same readiness, timezone and DST validation as .ics.
    start = next(line.split(':', 1)[1] for line in exported.split('\r\n') if line.startswith('DTSTART:'))
    end = next(line.split(':', 1)[1] for line in exported.split('\r\n') if line.startswith('DTEND:'))
    details = event.details
    if event.reminder_minutes is not None:
        details += f'\nRequested reminder: {event.reminder_minutes} minutes before. Set the notification in Google Calendar.'
    return {'url': 'https://calendar.google.com/calendar/render?' + urlencode({
        'action': 'TEMPLATE', 'text': event.title, 'dates': start + '/' + end,
        'ctz': event.timezone, 'details': details, 'location': event.location})}

class DeleteTasks(BaseModel):
    targets: list[dict[str, str]] = Field(min_length=1, max_length=1000)

@app.post('/api/tasks/delete')
def delete_tasks(body: DeleteTasks):
    targets = {(t.get('cid', ''), t.get('aid', '')) for t in body.targets}
    for cid, _ in targets:
        idle(cid)
    # One transaction: retain recordings/transcripts and remove only selected actions.
    with sqlite3.connect(DB) as conn:
        changed = {}
        for cid, aid in targets:
            if cid not in changed:
                row = conn.execute('SELECT body FROM conversations WHERE id=?', (cid,)).fetchone()
                if not row:
                    raise HTTPException(404, 'Conversation not found')
                changed[cid] = json.loads(row[0])
            item = changed[cid]
            if not any(a['id'] == aid for a in item['actions']):
                raise HTTPException(409, 'A selected task changed. Refresh and try again.')
            item['actions'] = [a for a in item['actions'] if a['id'] != aid]
            item.get('task_plans', {}).pop(aid, None)
        for cid, item in changed.items():
            conn.execute('UPDATE conversations SET body=? WHERE id=?', (json.dumps(item), cid))
    return {'deleted': len(targets)}

@app.get('/api/notifications')
def notifications():
    result = []
    now = datetime.now(timezone.utc)
    for item in conversations():
        if item.get('source') in ('sample', 'synthetic'):
            continue
        for raw in item['actions']:
            if raw['status'] != 'ready':
                continue
            a = Action.model_validate(raw)
            candidates = []
            deadline = item.get('task_plans', {}).get(a.id, {}).get('deadline')
            if deadline:
                candidates.append(('deadline', datetime.fromisoformat(deadline)))
            if a.type == 'event':
                try:
                    exported = calendar_export(a)
                    stamp = next(l.split(':', 1)[1] for l in exported.split('\r\n') if l.startswith('DTSTART:'))
                    start = datetime.strptime(stamp, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
                    from datetime import timedelta
                    candidates.append(('event reminder', start - timedelta(minutes=a.reminder_minutes or 0)))
                except ValueError:
                    pass
            for kind, when in candidates:
                if when <= now:
                    result.append({'id': f'{item["id"]}:{a.id}:{kind}:{when.isoformat()}',
                        'cid': item['id'], 'aid': a.id, 'title': a.title, 'kind': kind, 'at': when.isoformat()})
    return sorted(result, key=lambda n: n['at'], reverse=True)

@app.get('/api/conversations/{cid}/actions/{aid}/calendar')
def export(cid: str, aid: str):
    action = next((a for a in read(cid)['actions'] if a['id'] == aid), None)
    if not action:
        raise HTTPException(404, 'Action not found')
    return Response(calendar_export(Action.model_validate(action)), media_type='text/calendar', headers={'Content-Disposition': 'attachment; filename="followthrough.ics"'})

app.mount('/', StaticFiles(directory=ROOT / 'static', html=True), name='frontend')
