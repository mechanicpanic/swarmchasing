"""C33: parse a simulated task-clock date (month + day) from a wiki label.
Title-case month token (Jan..Dec, also full names and "Sept"), then a day: 1-2 digits not followed by another digit
(or exactly 2 digits followed by a 10+ digit timestamp, e.g. OpenAIResearchJan021781880284), or a spelled-out
day (MarTen, NovTwentySeven). Returns (tag, kind): tag "Mar28" or None; kind in digits | words | month_only |
multi | none. month_only (JuneScout, ResearchBotFeb2028: month with no day, or month + year) and multi (two
different dates) count as undated. A label is a name, not an agent."""
import re

MONTHS = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10,
          'Nov': 11, 'Dec': 12}
MON = r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?' \
      r'|Nov(?:ember)?|Dec(?:ember)?)'
ONES = ['One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen',
        'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
WORD = {w: i + 1 for i, w in enumerate(ONES)}
ONES_RE = '|'.join(sorted(ONES, key=len, reverse=True))
DIGITS = re.compile(MON + r'(\d{1,2})(?!\d)|' + MON + r'(\d{2})(?=\d{10,})')
WORDS = re.compile(MON + r'(Twenty|Thirty)?(' + ONES_RE + r')?(?![a-z])')
MONTH_ANY = re.compile(MON + r'(?![a-z])')


def _tag(mon, day):
    m = MONTHS[mon[:3]]
    return f'{mon[:3]}{day:02d}' if 1 <= day <= 31 and not (m == 2 and day > 29) else None


def parse(label):
    if not label:
        return None, 'none'
    tags = set()
    for m in DIGITS.finditer(label):
        mon, day = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        t = _tag(mon, int(day))
        if t: tags.add(t)
    kind = 'digits'
    if not tags:
        for m in WORDS.finditer(label):
            tens, ones = m.group(2), m.group(3)
            if not (tens or ones): continue
            if tens and ones and WORD[ones] > 9: continue
            t = _tag(m.group(1), {'Twenty': 20, 'Thirty': 30, None: 0}[tens] + (WORD[ones] if ones else 0))
            if t: tags.add(t)
        kind = 'words'
    if len(tags) == 1:
        return tags.pop(), kind
    if len(tags) > 1:
        return None, 'multi'
    return None, ('month_only' if MONTH_ANY.search(label) else 'none')


if __name__ == '__main__':
    for s in ['TransportHelperMar28OAI', 'OpenAIResearchJan021781880284', 'OpenAIFebSevenScout', 'AgentResearchNovTwentySeven',
              'JulSixteenPovertyWatcher', 'ResearchBotFeb2028', 'JuneScout', 'OpenAIJul8Watcher', 'MCV2June30Scout',
              'AgentLinkma21JuneAA', 'OpenAIFebScoutAlphaLumen', 'ResearchAgentJulTwentyThree', 'SepTenOECDScout',
              'AgentMassRefOctB', 'OpenAIHealthdataCVDSept08', 'OECDNov22R1781921290521770054', 'Apr25OECD288854078']:
        print(f'{s:36s} {parse(s)}')
