from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

def escape(value):
    return value.replace('\\', '\\\\').replace('\r', '').replace('\n', '\\n').replace(';', '\\;').replace(',', '\\,')

def fold(line):
    rows, current = [], ''
    for char in line:
        if len((current + char).encode('utf-8')) > 75:
            rows.append(current)
            current = ' '
        current += char
    return '\r\n'.join(rows + [current])

def calendar_export(action):
    if action.type != 'event' or action.status != 'ready' or action.certainty != 'confirmed' or action.missing:
        raise ValueError('Review and resolve this event before exporting.')
    if not action.date or not action.time or not action.duration_minutes:
        raise ValueError('Date, time and duration are required.')
    local = datetime.fromisoformat(f'{action.date}T{action.time}')
    if local.tzinfo:
        raise ValueError('Use a local HH:MM time and the separate timezone field.')
    zone = ZoneInfo(action.timezone)
    start = local.replace(tzinfo=zone)
    if start.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != local:
        raise ValueError('This local time does not exist due to daylight saving time.')
    if start.utcoffset() != local.replace(tzinfo=zone, fold=1).utcoffset():
        raise ValueError('This local time is ambiguous due to daylight saving time. Choose a different time.')
    start = start.astimezone(timezone.utc)
    stamp = lambda dt: dt.strftime('%Y%m%dT%H%M%SZ')
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//FollowThrough//EN', 'CALSCALE:GREGORIAN', 'BEGIN:VEVENT',
        f'UID:{escape(action.id)}@followthrough.local', f'DTSTAMP:{stamp(datetime.now(timezone.utc))}',
        f'DTSTART:{stamp(start)}', f'DTEND:{stamp(start + timedelta(minutes=action.duration_minutes))}',
        'SUMMARY:' + escape(action.title), 'LOCATION:' + escape(action.location),
        'DESCRIPTION:' + escape(action.details + '\nOriginal timezone: ' + action.timezone)]
    if action.reminder_minutes is not None:
        lines += ['BEGIN:VALARM', f'TRIGGER:-PT{action.reminder_minutes}M', 'ACTION:DISPLAY', 'DESCRIPTION:FollowThrough reminder', 'END:VALARM']
    lines += ['END:VEVENT', 'END:VCALENDAR']
    return '\r\n'.join(fold(line) for line in lines) + '\r\n'
