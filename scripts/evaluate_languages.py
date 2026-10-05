"""Live text-only multilingual checks; not an ASR accuracy benchmark."""
import asyncio
import json
from pathlib import Path
from app.inference import understand

CASES = [
    ('english', 'May be ask Rahul to join. Do not send the recap yet.', 'original'),
    ('hindi', 'कल शाम सात बजे लाइब्रेरी में 30 मिनट के लिए मिलते हैं। HDMI adapter 800 रुपये से कम का चाहिए, लेकिन अभी मत खरीदो।', 'English'),
    ('tamil', 'நாளை மாலை ஏழு மணிக்கு library-யில் 30 நிமிடங்கள் சந்திப்போம். Prototype கொண்டு வா. HDMI adapter 800 ரூபாய்க்குள் வேண்டும், ஆனால் இப்போது வாங்காதே.', 'original'),
    ('tanglish', 'Bro naalai evening 7 mani ku library la meet pannalam, 30 minutes. Prototype eduthutu va. HDMI adapter 800 rupees kulla venum, aana ippo vaangadha.', 'English'),
    ('wording', 'Bring the proton type to the prototype demo.', 'original'),
]

async def main():
    results = []
    for name, source, language in CASES:
        result = None
        try:
            result = await understand(source, '2026-10-05T10:00:00+05:30', 'Asia/Kolkata', 'concise', language)
            assert result.detected_languages, 'No detected languages'
            if name == 'english':
                assert 'maybe' in result.recap.lower().replace('may be', 'maybe'), 'Lost maybe in recap'
                assert any(s in result.recap.lower() for s in ['not', "don't", 'wait']), 'Lost negation in recap'
                assert not any('\u0b80' <= c <= '\u0bff' for c in result.recap), 'Unexpected translation'
            if name in ('hindi', 'tamil', 'tanglish'):
                assert any(a.type == 'event' and a.time == '19:00' and a.date == '2026-10-06' for a in result.actions), 'Wrong daypart'
                shopping = [a for a in result.actions if a.type == 'shopping']
                assert shopping and shopping[0].budget_inr == 800, 'Lost budget'
                assert shopping[0].status == 'needs clarification', 'Lost prohibition'
            if name == 'wording':
                assert result.language_issues, 'Suspicious wording not flagged'
            results.append({'case': name, 'passed': True, 'output': result.model_dump()})
        except Exception as exc:
            results.append({'case': name, 'passed': False, 'error': str(exc),
                'output': result.model_dump() if result else None})
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)
    Path('artifacts/language-evaluation.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    return all(r['passed'] for r in results)

if __name__ == '__main__':
    raise SystemExit(0 if asyncio.run(main()) else 1)
