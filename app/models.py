from datetime import datetime
import re
from typing import Literal
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field, ConfigDict, field_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Action(Strict):
    id: str = ''
    type: Literal['event', 'task', 'shopping', 'draft', 'question', 'decision']
    title: str = Field(min_length=1, max_length=200)
    evidence: str = Field(min_length=1, max_length=3000)
    certainty: Literal['confirmed', 'tentative', 'conditional'] = 'confirmed'
    status: Literal['needs clarification', 'ready', 'completed', 'dismissed'] = 'ready'
    missing: list[str] = Field(default_factory=list, max_length=20)
    details: str = Field(default='', max_length=5000)
    date: str = Field(default='', pattern=r'^$|^\d{4}-\d{2}-\d{2}$')
    time: str = Field(default='', pattern=r'^$|^(?:[01]\d|2[0-3]):[0-5]\d$')
    timezone: str = 'Asia/Kolkata'
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    reminder_minutes: int | None = Field(default=None, ge=0, le=10080)
    location: str = ''
    owner: str = ''
    due: str = ''
    product: str = ''
    budget_inr: float | None = Field(default=None, ge=0)
    quantity: int | None = Field(default=None, ge=1, le=10000)
    compatibility: str = ''

class LanguageIssue(Strict):
    quote: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=1000)
    suggestion: str = Field(default='', max_length=1000)

class Understanding(Strict):
    title: str = Field(min_length=1, max_length=200)
    recap: str = Field(max_length=12000)
    actions: list[Action] = Field(max_length=40)
    detected_languages: list[str] = Field(default_factory=list, max_length=10)
    language_issues: list[LanguageIssue] = Field(default_factory=list, max_length=12)
    recap_warnings: list[str] = Field(default_factory=list, max_length=20)

class RecapReview(Strict):
    recap: str = Field(max_length=12000)
    detected_languages: list[str] = Field(max_length=10)
    language_issues: list[LanguageIssue] = Field(max_length=12)

class Extraction(Strict):
    title: str = Field(min_length=1, max_length=200)
    recap: str = Field(max_length=12000)
    actions: list[Action] = Field(max_length=40)

class ConversationInput(Strict):
    transcript: str = Field(default='', max_length=40000)
    recorded_at: str
    timezone: str = 'Asia/Kolkata'
    style: Literal['casual', 'concise', 'professional'] = 'casual'
    output_language: Literal['original', 'English', 'Tamil', 'Hindi', 'Telugu', 'Kannada', 'Malayalam', 'Spanish', 'French', 'German'] = 'original'
    @field_validator('recorded_at')
    @classmethod
    def valid_date(cls, value):
        if datetime.fromisoformat(value).tzinfo is None:
            raise ValueError('Recording time must include a UTC offset')
        return value
    @field_validator('timezone')
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except Exception as exc:
            raise ValueError('Use a valid IANA timezone, such as Asia/Kolkata.') from exc
        return value

def validate_understanding(result: Understanding, transcript: str, reviewed=False):
    for issue in result.language_issues:
        if issue.quote not in transcript:
            raise ValueError('A language review cites text that is not in the transcript.')
    for action in result.actions:
        if action.evidence not in transcript:
            raise ValueError('An action cites text that is not in the transcript. Please retry.')
        action.id = ''
        # Model output is a proposal, never a completed/executed action.
        action.status = 'ready'
        if not reviewed:
            for issue in result.language_issues:
                if issue.quote in action.evidence or action.evidence in issue.quote:
                    action.missing.append('Review possible transcription mismatch: ' + issue.reason)
            # Conservative English evidence checks supplement, not replace, Gemma.
            # Human review can confirm a time or commitment afterwards.
            position = transcript.find(action.evidence)
            sentence_start = max(transcript.rfind(mark, 0, position) for mark in '.!?।') + 1
            evidence_end = position + len(action.evidence)
            suffix_end = re.search(r'[.!?।]', transcript[evidence_end:])
            sentence_end = evidence_end if action.evidence.rstrip().endswith(('.', '!', '?', '।')) else (
                evidence_end + suffix_end.end() if suffix_end else len(transcript))
            context = transcript[sentence_start:sentence_end]
            if action.type == 'shopping':
                following = transcript[position + len(action.evidence):]
                next_sentence = re.match(r'^[\s.!?]*(.*?[.!?]|.*$)', following)
                if next_sentence and re.search(r"\bwait\b|\bdo not\b|\bdon['’]t\b|\buntil\b", next_sentence.group(1), re.I):
                    context += ' ' + next_sentence.group(1)
                    action.missing.append('Confirm the shopping condition: ' + next_sentence.group(1).strip())
            if re.search(r'\bmay\s*be\b|\bperhaps\b|\bshayad\b|ஒருவேளை|शायद', context, re.I):
                action.certainty = 'tentative'
            if action.type != 'decision' and re.search(r"\bdo not\b|\bdon['’]t\b|\bwait until\b|\bnot yet\b|வாங்காத|அனுப்பாத|வேண்டாம்|मत खरीद|मत भेज|\b(?:vaangadha|vaangaadha|vangadha|vendam|vendaam)\b", context, re.I):
                action.certainty = 'conditional'
            if action.type == 'event' and action.time:
                explicit = re.search(r'(?<![a-z])[ap]\.?\s*m\.?\b|\b(?:morning|afternoon|evening|night|noon|midnight)\b|\b(?:1[3-9]|2[0-3]):[0-5]\d\b|\b(?:00|0[1-9]):[0-5]\d\b', action.evidence, re.I)
                # Recognize common native/transliterated dayparts. A script alone
                # is not proof of AM/PM; unsupported ambiguous wording needs review.
                multilingual_daypart = re.search(
                    r'\b(?:maalai|malai|kaalai|kalai|iravu|subah|shaam|sham|raat|dopahar|matin|soir|après-midi|abends|morgens|nachmittags)\b'
                    r'|மாலை|காலை|இரவு|மதியம்|शाम|सुबह|रात|दोपहर|संध्या'
                    r'|ఉదయం|సాయంత్రం|రాత్రి|మధ్యాహ్నం|ಬೆಳಿಗ್ಗೆ|ಸಂಜೆ|ರಾತ್ರಿ|ಮಧ್ಯಾಹ್ನ'
                    r'|രാവിലെ|വൈകുന്നേരം|രാത്രി|ഉച്ച|por la mañana|de la tarde|de la noche', action.evidence, re.I)
                if not explicit and not multilingual_daypart:
                    action.time = ''
                    action.missing.append('Confirm the time, including AM or PM.')
        if action.certainty != 'confirmed' and not action.missing:
            action.missing.append('Confirm whether you want to proceed with this tentative or conditional action.')
        if action.type == 'question' and not action.missing and not reviewed:
            action.missing.append(action.title)
        if action.type == 'event':
            if action.date:
                datetime.strptime(action.date, '%Y-%m-%d')
            if not action.date:
                action.missing.append('Confirm the calendar date.')
            if not action.time:
                action.missing.append('Confirm the time, including AM or PM.')
            if not action.duration_minutes:
                action.missing.append('Confirm the meeting duration.')
            if action.date and action.time:
                datetime.fromisoformat(f'{action.date}T{action.time}')
            try:
                ZoneInfo(action.timezone)
            except Exception as exc:
                raise ValueError('Use a valid IANA timezone, such as Asia/Kolkata.') from exc
        if action.missing:
            action.missing = list(dict.fromkeys(action.missing))
            action.status = 'needs clarification'
    return result
