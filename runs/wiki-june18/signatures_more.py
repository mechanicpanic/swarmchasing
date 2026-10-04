import pickle, collections, re, difflib, random

OUT = './out/'  # intermediates
rows = pickle.load(open(OUT + 'rows.pkl', 'rb'))
saves, mis, ex = pickle.load(open(OUT + 'mis.pkl', 'rb'))
labels_all = collections.Counter(r['label'] for r in rows)

DT = re.compile(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[-_]?(\d{1,2})(?!\d)', re.I)
WORDS = {'jan': 'jan', 'feb': 'feb', 'mar': 'mar', 'apr': 'apr', 'may': 'may', 'jun': 'jun', 'jul': 'jul', 'aug': 'aug', 'sep': 'sep', 'oct': 'oct', 'nov': 'nov', 'dec': 'dec'}
NUMW = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12}


def dates(s):
    out = set()
    for m in DT.finditer(s):
        out.add((m.group(1).lower()[:3], int(m.group(2))))
    m = re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)', s, re.I)
    if m:
        out.add((m.group(1).lower()[:3], NUMW[m.group(2).lower()]))
    return out


# date relation
rel = collections.Counter(); exd = collections.defaultdict(list)
for s in mis:
    dl, ds = dates(s['L']), dates(s['last'])
    if dl and ds:
        k = 'same_date' if dl & ds else 'different_date'
    elif dl or ds:
        k = 'date_on_one_side'
    else:
        k = 'no_dates'
    s['drel'] = k; rel[k] += 1; exd[k].append(s)
print('date relation label vs sig (mismatches)', rel)
rm = collections.Counter()
for s in saves:
    if s['match']:
        rm['has_date' if dates(s['L']) else 'no_date'] += 1
print('matched: label has date', rm)

# random-suffix labels (rotation): label = stem + long digit run
rot = [s for s in mis if re.search(r'\d{5,}$', s['L'])]
print('mismatch labels ending in >=5 digits', len(rot), 'of which same date as sig', sum(s['drel'] == 'same_date' for s in rot))
for s in rot[:6]:
    print('   ', s['r']['time'], s['L'], '->', s['last'], labels_all[s['L']])

# fuzzy relay check: is the signed line similar to an earlier line with same signature?
prior = collections.defaultdict(list)  # sig -> [(t, line, label)]
for r in rows:
    for x in r['sigs']:
        prior[x['name']].append((r['t'], x['line'], r['label']))
RELAY_W = re.compile(r'(?i)\b(relay(?:ing|ed)?|forward(?:ing|ed)?|quot(?:e|ing)|reposted|copied from|from @?[A-Z]\w+:|via @?[A-Z]\w+|on behalf)')


def fuzzy_prior(s):
    t = s['r']['t']; line = s['new'][-1]['line']; best = 0; who = None
    for tt, l2, lab in prior[s['last']]:
        if tt < t:
            r = difflib.SequenceMatcher(None, line, l2).quick_ratio()
            if r > best:
                r = difflib.SequenceMatcher(None, line, l2).ratio()
                if r > best:
                    best, who = r, lab
    return best, who


fz = collections.Counter(); fzm = collections.Counter()
random.seed(3)
for s in mis:
    b, who = fuzzy_prior(s); s['fz'] = b; s['fz_who'] = who
    fz['>=0.8' if b >= .8 else '0.5-0.8' if b >= .5 else '<0.5'] += 1
for s in random.sample([s for s in saves if s['match']], 1000):
    b, _ = fuzzy_prior(s)
    fzm['>=0.8' if b >= .8 else '0.5-0.8' if b >= .5 else '<0.5'] += 1
print('mismatched: similarity of signed line to an earlier line with same sig', fz)
print('matched (sample 1000):', fzm)
print('relay words in mismatched line', sum(bool(RELAY_W.search(s['new'][-1]['line'])) for s in mis) / len(mis),
      'matched', sum(bool(RELAY_W.search(s['new'][-1]['line'])) for s in saves if s['match']) / sum(s['match'] for s in saves))
# first-person indicators
FP = re.compile(r'(?i)\b(our|we|I|my)\b')
print('first-person words: mismatched', round(sum(bool(FP.search(s['new'][-1]['line'])) for s in mis) / len(mis), 3),
      'matched', round(sum(bool(FP.search(s['new'][-1]['line'])) for s in saves if s['match']) / sum(s['match'] for s in saves), 3))
# signature date == date mentioned in first words of line ("Aug25 5m26 cohort", "NOV09 R2")
def selfref(s):
    d = dates(s['last']); return bool(d & dates(s['new'][-1]['line'][:60]))
print('line opens with signer\'s own cohort date: mismatched', round(sum(selfref(s) for s in mis) / len(mis), 3),
      'matched', round(sum(selfref(s) for s in saves if s['match'] and dates(s['last'])) / max(1, sum(1 for s in saves if s['match'] and dates(s['last']))), 3))

# ---- time clustering
def day(s): return s['r']['time'][:10]
dm = collections.Counter(day(s) for s in mis); da = collections.Counter(day(s) for s in saves)
print('\nby day: day, signed saves, mismatches, rate')
for d in sorted(da):
    if da[d] >= 20:
        print('  ', d, da[d], dm[d], f'{dm[d]/da[d]:.2f}')
hm = collections.Counter(s['r']['time'][:13] for s in mis); ha = collections.Counter(s['r']['time'][:13] for s in saves)
print('top hours by mismatch count:', [(h, hm[h], ha[h]) for h, _ in hm.most_common(10)])
pm = collections.Counter(s['r']['page'] for s in mis); pa = collections.Counter(s['r']['page'] for s in saves)
print('pages with mismatches:', len(pm), 'of', len(pa), 'signed pages; top:', [(p, pm[p], pa[p]) for p, _ in pm.most_common(10)])
top10 = sum(c for _, c in pm.most_common(10)); print('top10 pages share of mismatches', round(top10 / len(mis), 3))
lm = collections.Counter(s['L'] for s in mis)
print('labels on mismatches:', len(lm), 'top:', lm.most_common(10))
sm = collections.Counter(s['last'] for s in mis)
print('signers in mismatches:', len(sm), 'top:', sm.most_common(8))
# Hour-of-day concentration
hod = collections.Counter(int(s['r']['time'][11:13]) for s in mis); hoda = collections.Counter(int(s['r']['time'][11:13]) for s in saves)
print('rate by UTC hour:', [(h, hod[h], hoda[h], round(hod[h]/hoda[h], 2)) for h in range(24) if hoda[h] >= 30])
pickle.dump(mis, open(OUT + 'mis2.pkl', 'wb'))
