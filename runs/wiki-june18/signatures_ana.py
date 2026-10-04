import pickle, collections, re, random, bisect
from datetime import datetime, timezone

OUT = './out/'  # intermediates
rows = pickle.load(open(OUT + 'rows.pkl', 'rb'))
W = 10 * 60  # window seconds

labels_all = collections.Counter(r['label'] for r in rows if r['label'])
by_label = collections.defaultdict(list)          # label -> [(t, ip16, page)]
for r in rows:
    by_label[r['label']].append((r['t'], r['ip16'], r['page']))
sig_events = collections.defaultdict(list)         # signature name -> [(t, label, ip16, page)]
for r in rows:
    for s in r['sigs']:
        if s['fresh'] == 'new':
            sig_events[s['name']].append((r['t'], r['label'], r['ip16'], r['page']))
for v in sig_events.values():
    v.sort()
label_times = {k: sorted(x[0] for x in v) for k, v in by_label.items()}

MONTH = r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\d{0,2}'


def stem(s):
    s = s.lower()
    s = re.sub(MONTH, '', s)
    s = re.sub(r'\d+', '', s)
    s = re.sub(r'(oai|openai|x|y|z)+$', '', s)
    s = re.sub(r'^(oai|openai)', '', s)
    return s


def lev(a, b):
    a, b = a.lower(), b.lower()
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def date_tok(s):
    m = re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\d{1,2}', s.lower())
    return m.group(0) if m else None


def any_in(times, lo, hi):
    i = bisect.bisect_left(times, lo)
    return i < len(times) and times[i] <= hi


def label_recent(L, t, ip=None, exclude_t=None):
    for (tt, ii, pg) in by_label.get(L, []):
        if t - W <= tt < t and (ip is None or ii == ip):
            return True
    return False


def sig_recent(L, t, exclude_label=None):
    """L appears as a NEW signature in another save within the previous W."""
    for (tt, lab, ii, pg) in sig_events.get(L, []):
        if t - W <= tt < t:
            return True
    return False


# ---------- save-level classification
BURST = (datetime(2026, 6, 18, 20, 9, 0, tzinfo=timezone.utc).timestamp(), datetime(2026, 6, 18, 20, 15, 0, tzinfo=timezone.utc).timestamp())
saves = []
for r in rows:
    new = [s for s in r['sigs'] if s['fresh'] == 'new']
    if not new:
        continue
    names = [s['name'] for s in new]
    L = r['label']
    match = L in names
    ci = any(n.lower() == L.lower() for n in names)
    saves.append(dict(r=r, new=new, names=names, L=L, match=match, ci=ci, last=new[-1]['name']))

n = len(saves); nm = sum(s['match'] for s in saves)
print(f'saves with new signature: {n}; label==some sig: {nm} ({nm/n:.1%}); case-insens extra {sum(s["ci"] and not s["match"] for s in saves)}')
mis = [s for s in saves if not s['match']]
print('mismatched saves', len(mis), 'of which multi-sig saves', sum(len(set(s['names'])) > 1 for s in mis))
inburst = [s for s in mis if BURST[0] <= s['r']['t'] <= BURST[1]]
print('mismatches in 20:09-20:15 Jun18 burst', len(inburst))


def classify(s):
    L, sig, r = s['L'], s['last'], s['r']
    t, ip = r['t'], r['ip16']
    if L == '':
        return 'blank_label'
    if sig.lower() == L.lower():
        return 'case_only'
    d = lev(L, sig)
    if stem(L) == stem(sig) or d <= 3 or (len(sig) >= 6 and (sig.lower() in L.lower() or L.lower() in sig.lower())):
        return 'near_miss'
    if label_recent(sig, t, ip):
        return 'sig_is_label_recent_same_ip16'
    if label_recent(sig, t):
        return 'sig_is_label_recent_10min'
    if sig in labels_all:
        return 'sig_is_known_label_other_time'
    return 'sig_never_a_label'


cls = collections.Counter()
ex = collections.defaultdict(list)
for s in mis:
    c = classify(s); s['cls'] = c; cls[c] += 1
    ex[c].append(s)
print('taxonomy (by last new sig):', cls.most_common())

# sub-detail near_miss: what differs
sub = collections.Counter()
for s in ex['near_miss']:
    a, b = s['L'], s['last']
    da, db = date_tok(a), date_tok(b)
    if da and db and da != db:
        sub['different_date'] += 1
    elif stem(a) == stem(b):
        sub['same_stem_other_suffix'] += 1
    else:
        sub['edit<=3/substring'] += 1
print('near-miss detail', sub)

# label profile for mismatches: is L a one-shot label? does L ever sign?
def prof(group):
    one = sum(labels_all[s['L']] <= 2 for s in group)
    signs = sum(s['L'] in sig_events for s in group)
    selfsig = sum(any(x[1] == s['last'] for x in sig_events.get(s['last'], [])) for s in group)
    return dict(n=len(group), L_le2_saves=one, L_ever_signs=signs, sig_ever_self_labelled=selfsig)
print('mismatch label profile', prof([s for s in mis if s['L']]))
print('matched label profile', prof([s for s in saves if s['match']]))

pickle.dump((saves, mis, ex), open(OUT + 'mis.pkl', 'wb'))

# ---------- examples
for c, lst in ex.items():
    print('\n==', c, len(lst))
    random.seed(7)
    for s in random.sample(lst, min(4, len(lst))):
        r = s['r']
        print(' ', r['time'], r['page'], 'label=', repr(s['L']), 'ip16', r['ip16'], 'sig=', s['last'])
        print('    ', repr(s['new'][-1]['line'][-200:]))
