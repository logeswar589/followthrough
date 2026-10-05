"""Conservative recap checks. These flag possible omissions, not proven errors."""
import re
from datetime import timedelta

def anchor_relative_dates(actions, local_recording):
    """Anchor unambiguous supported day words; ask if competing anchors occur."""
    terms = [(1, r'\btomorrow\b|\bnaalai\b|நாளை|రేపు|നാളെ|ನಾಳೆ'),
        (0, r'\btoday\b|\binnik[ku]*\b|இன்று|ఈరోజు|ഇന്ന്|ಇಂದು'),
        (-1, r'\byesterday\b|\bnetru\b|நேற்று|నిన్న|ഇന്നലെ|ನಿನ್ನೆ')]
    for action in actions:
        if action.type != 'event':
            continue
        offsets = {offset for offset, pattern in terms if re.search(pattern, action.evidence, re.I)}
        if not offsets:
            continue
        competing = re.search(r'\b(?:next|instead|actually|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b|\d{4}-\d{2}-\d{2}|கிழமை|அடுத்த|பதிலாக', action.evidence, re.I)
        if len(offsets) == 1:
            expected = (local_recording.date() + timedelta(days=next(iter(offsets)))).isoformat()
            if action.date == expected:
                continue
            if not competing:
                action.date = expected
                continue
        action.date = ''
        action.missing.append('Confirm the intended date: the relative day and extracted date disagree or have competing corrections.')

MARKERS = {
    'uncertainty': r'\bmay\s*be\b|\bperhaps\b|\bpossibly\b|\bshayad\b|ஒருவேளை|शायद|हो सकता|tal vez|peut-être|vielleicht',
    'prohibition or waiting condition': r"\bdo not\b|\bdon['’]t\b|\bnot yet\b|\bwait\b|\buntil\b|வாங்காத|அனுப்பாத|வேண்டாம்|காத்திரு|मत खरीद|मत भेज|अभी नहीं|इंतजार|vaangadha|vaangaadha|vendam|vendaam|no compres|n'ach|nicht kaufen",
    'tomorrow': r'\btomorrow\b|\bnaalai\b|நாளை|कल|రేపు|നാളെ|ನಾಳೆ|demain|mañana|morgen',
}
SCRIPTS = [('Tamil', '\u0b80', '\u0bff'), ('Devanagari', '\u0900', '\u097f'),
    ('Telugu', '\u0c00', '\u0c7f'), ('Kannada', '\u0c80', '\u0cff'), ('Malayalam', '\u0d00', '\u0d7f')]

def wording_checks(source):
    """Flag a split Latin-script term resembling another term in this recording.

    This is a consistency hint, not a dictionary or an automatic correction.
    Require an existing source term and just one added/dropped letter.
    """
    tokens = list(re.finditer(r'[A-Za-z]{3,}', source))
    known = {t.group().lower(): t.group() for t in tokens if len(t.group()) >= 8}
    issues = []
    for left, right in zip(tokens, tokens[1:]):
        if not source[left.end():right.start()].isspace():
            continue
        joined = (left.group() + right.group()).lower()
        for normalized, original in known.items():
            if abs(len(normalized) - len(joined)) != 1 or normalized[:3] != joined[:3]:
                continue
            longer, shorter = sorted([normalized, joined], key=len, reverse=True)
            if not any(longer[:i] + longer[i+1:] == shorter for i in range(len(longer))):
                continue
            issues.append({'quote': source[left.start():right.end()],
                'reason': f'This split phrase resembles “{original}” elsewhere in the transcript. Were they meant to be the same term?',
                'suggestion': original})
            break
        if len(issues) >= 12:
            break
    return issues

def recap_checks(source, recap, actions, output_language):
    warnings = []
    for label, pattern in MARKERS.items():
        if re.search(pattern, source, re.I) and not re.search(pattern, recap, re.I):
            warnings.append(f'The recap may have lost {label}; compare with the source before using it.')
    for action in actions:
        if action.budget_inr is not None:
            amount = f'{action.budget_inr:g}'
            if amount not in recap.replace(',', ''):
                warnings.append(f'Check the budget: {amount} INR is not explicit in the recap.')
    if output_language == 'original':
        for label, low, high in SCRIPTS:
            if any(low <= c <= high for c in source) != any(low <= c <= high for c in recap):
                warnings.append(f'The recap changed the source script ({label}); check the language choice.')
    return list(dict.fromkeys(warnings))
