"""C28 steps 1-4: owners, borrowed uses, 10-min-after-owner share, four nulls, before-first-use and swaps."""
import bisect, collections, pickle, random, statistics, sys

OUT = __import__('os').environ.get('OUT', 'results/c28/')
rows = pickle.load(open(OUT + 'rows.pkl', 'rb'))
W = 600
NREP = 500
OWNER_DEF = sys.argv[1] if len(sys.argv) > 1 else 'most'   # most | first | self (PR #7: L itself if L self-signs)

# ---- signed saves (new signed lines only, as PR #7)
saves = []
for r in rows:
    new = [s for s in r['sigs'] if s['fresh'] == 'new']
    if new:
        names = list(dict.fromkeys(s['name'] for s in new))
        saves.append(dict(r=r, L=r['label'], names=names, last=new[-1]['name'], line=new[-1]['line'],
                          row_id=new[-1]['row_id'], match=r['label'] in names))
n = len(saves); nm = sum(s['match'] for s in saves)
print(f'signed saves {n}; label==a signature {nm} ({nm / n:.1%}); mismatches {n - nm}; blank-label mismatches',
      sum(1 for s in saves if not s['match'] and not s['L']))

# ---- owners
by_L = collections.defaultdict(list)
for s in saves:
    if s['L']:
        by_L[s['L']].append(s)
owner = {}
for L, lst in by_L.items():
    if OWNER_DEF == 'self':
        if any(s['match'] for s in lst):
            owner[L] = L
        continue
    cnt = collections.Counter(); first = {}
    for s in lst:  # time order
        for nme in s['names']:
            cnt[nme] += 1; first.setdefault(nme, s['r']['t'])
    if OWNER_DEF == 'first':
        owner[L] = lst[0]['names'][0]
    else:
        owner[L] = max(cnt, key=lambda k: (cnt[k], -first[k]))
print(f'owner def={OWNER_DEF}: labels with signed saves {len(by_L)}, with owner {len(owner)}, '
      f'owner==label {sum(o == L for L, o in owner.items())}')

STRICT = len(sys.argv) > 2 and sys.argv[2] == 'strict'
import re


def lev(a, b):
    a, b = a.lower(), b.lower()
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def near(a, b):  # PR #7 near-miss: same name up to case, edit distance <=3, or one contains the other (>=5 chars)
    a2, b2 = a.lower(), b.lower()
    return a2 == b2 or lev(a, b) <= 3 or (min(len(a2), len(b2)) >= 5 and (a2 in b2 or b2 in a2))


akey_seen = set()
for s in saves:  # re-save detector: the signed line, ASCII letters/digits only, seen in an earlier save
    k = re.sub(r'[^A-Za-z0-9]', '', s['line'])
    s['resave'] = k in akey_seen
    akey_seen.add(k)

own_ev = collections.defaultdict(list)   # L -> times of saves under L signed by owner(L)
borrowed = []
drop = collections.Counter()
for s in saves:
    L = s['L']
    if L not in owner:
        continue
    o = owner[L]
    if not STRICT:
        if o in s['names']:
            own_ev[L].append((s['r']['t'], s['r']['rev_id']))
        else:
            borrowed.append(s)
        continue
    if any(nm == o or nm == L or near(nm, o) or near(nm, L) for nm in s['names']):
        own_ev[L].append((s['r']['t'], s['r']['rev_id']))
    elif s['resave']:
        drop['re-save of an earlier signed line (encoding drift)'] += 1
    else:
        borrowed.append(s)
if STRICT:
    print('strict: dropped', dict(drop))
for v in own_ev.values():
    v.sort()
own_t = {L: [t for t, _ in v] for L, v in own_ev.items()}
print(f'borrowed uses {len(borrowed)} on {len({s["L"] for s in borrowed})} labels; '
      f'owner saves {sum(len(v) for v in own_ev.values())}; labels with >=1 borrowed and >=2 owner saves',
      len({s['L'] for s in borrowed if len(own_t.get(s['L'], [])) >= 2}))


def hit(L, t, times=None):
    ts = own_t.get(L, []) if times is None else times
    i = bisect.bisect_left(ts, t - W)
    return i < len(ts) and ts[i] < t


def share(items, tt=None):
    return sum(hit(L, t, None if tt is None else tt.get(L)) for L, t in items) / len(items)


items = [(s['L'], s['r']['t']) for s in borrowed]
real = share(items)
print(f'\nSTAT share of borrowed uses within {W // 60} min after an owner save under L: {real:.3f} '
      f'({sum(hit(L, t) for L, t in items)}/{len(items)})')


def summ(v, real):
    v = sorted(v)
    return (f'median {statistics.median(v):.3f}  95th {v[int(.95 * len(v)) - 1]:.3f}  '
            f'share>=real {sum(x >= real for x in v) / len(v):.3f}')


DAY = 86400
rng = random.Random(1)

# (a) PR #7: shuffle borrowed-use times within the day
byday = collections.defaultdict(list)
for i, (L, t) in enumerate(items):
    byday[int(t // DAY)].append(i)


def null_a():
    out = list(items)
    for idx in byday.values():
        ts = [items[i][1] for i in idx]; rng.shuffle(ts)
        for i, t in zip(idx, ts):
            out[i] = (items[i][0], t)
    return share(out)


print('(a) borrowed times shuffled within day     ', summ([null_a() for _ in range(NREP)], real))


# (b) owner's saves under L moved as a block within the same day: gaps (rhythm) and day kept
def null_b(maxshift=None):
    tt = {}
    for L, ts in own_t.items():
        out = []
        groups = collections.defaultdict(list)
        for t in ts:
            groups[int(t // DAY)].append(t)
        for d, g in groups.items():
            lo, hi = d * DAY - g[0], (d + 1) * DAY - 1 - g[-1]
            if maxshift:
                lo, hi = max(lo, -maxshift), min(hi, maxshift)
            off = rng.uniform(lo, hi) if hi > lo else 0
            out += [t + off for t in g]
        tt[L] = sorted(out)
    return share(items, tt)


print('(b) owner block shifted within its day     ', summ([null_b() for _ in range(NREP)], real))
print("(b') owner block shifted <=3h, same day    ", summ([null_b(3 * 3600) for _ in range(NREP)], real))

# (c) permute labels among borrowed saves within (day, page); only groups with >=2 distinct labels
grp = collections.defaultdict(list)
for i, s in enumerate(borrowed):
    grp[(int(s['r']['t'] // DAY), s['r']['page'])].append(i)
perm = [g for g in grp.values() if len({items[i][0] for i in g}) >= 2]
sub = [i for g in perm for i in g]
real_c = sum(hit(*items[i]) for i in sub) / len(sub)


def null_c():
    hits = 0
    for g in perm:
        labs = [items[i][0] for i in g]; rng.shuffle(labs)
        hits += sum(hit(Lp, items[i][1]) for Lp, i in zip(labs, g))
    return hits / len(sub)


print(f'(c) labels permuted within (day,page): subset n={len(sub)} in {len(perm)} groups, real {real_c:.3f}; ',
      summ([null_c() for _ in range(NREP)], real_c))

# (d) same hour, another owned label: did ITS owner save under it in the 10 min before t?
hour_pool = collections.defaultdict(list)   # hour -> [(label, rev)] for owned labels, save-weighted
for r in rows:
    if r['label'] in own_t:
        hour_pool[int(r['t'] // 3600)].append((r['label'], r['rev_id']))


def null_d():
    h = 0
    for s in borrowed:
        L, t = s['L'], s['r']['t']
        pool = [x for x, rv in hour_pool[int(t // 3600)] if x != L and rv != s['r']['rev_id']]
        Lp = rng.choice(pool) if pool else L
        h += hit(Lp, t)
    return h / len(borrowed)


print('(d) another owned label active same hour   ', summ([null_d() for _ in range(NREP)], real))

# ---- step 4: position vs owner span; swaps
pos = collections.Counter()
for L, t in items:
    ts = own_t.get(L)
    if not ts:
        pos['owner never saves under L (only borrowed)'] += 1
    elif t < ts[0]:
        pos['before owner first save'] += 1
    elif t > ts[-1]:
        pos['after owner last save'] += 1
    else:
        pos['within owner span'] += 1
print('\nposition of borrowed uses vs owner span', dict(pos))
cnts = []
for _ in range(200):
    out = list(items)
    for idx in byday.values():
        ts = [items[i][1] for i in idx]; rng.shuffle(ts)
        for i, t in zip(idx, ts):
            out[i] = (items[i][0], t)
    c = collections.Counter()
    for L, t in out:
        ts = own_t.get(L)
        if ts:
            c['before' if t < ts[0] else 'after' if t > ts[-1] else 'within'] += 1
    cnts.append(c)
for k in ('before', 'within', 'after'):
    v = sorted(c[k] for c in cnts); print(f'   null(a) {k}: median {statistics.median(v)} p5-p95 {v[9]}-{v[189]}')

# swaps: borrowed (label L, signer S) and, within +-30 min, a save labelled S signed by owner(L)
lab_saves = collections.defaultdict(list)
for s in saves:
    lab_saves[s['L']].append(s)
swaps = []; S_is_label = 0
for s in borrowed:
    L, S, t = s['L'], s['last'], s['r']['t']
    if S in lab_saves:
        S_is_label += 1
    for o in lab_saves.get(S, []):
        if owner[L] in o['names'] and abs(o['r']['t'] - t) <= 1800:
            swaps.append((s['r']['rev_id'], o['r']['rev_id'])); break
print(f'swaps within 30 min: {len(swaps)} of {len(borrowed)} (borrower signature S is itself a label in {S_is_label})',
      swaps[:5])

# extra: gap from the latest owner save to the borrowed use, and same-page share, for in-window uses
gaps = []; same_page = 0
own_full = {L: v for L, v in own_ev.items()}
rev_page = {r['rev_id']: r['page'] for r in rows}
inw = []
for s in borrowed:
    L, t = s['L'], s['r']['t']
    ts = own_t.get(L, [])
    i = bisect.bisect_left(ts, t) - 1
    if i >= 0 and t - ts[i] <= W and ts[i] < t:
        gaps.append(t - ts[i]); inw.append(s)
        same_page += rev_page[own_full[L][i][1]] == s['r']['page']
if gaps:
    g = sorted(gaps)
    print(f'in-window: n={len(g)} gap s median {statistics.median(g):.0f} p25 {g[len(g) // 4]:.0f} '
          f'p75 {g[3 * len(g) // 4]:.0f}; <=60s {sum(x <= 60 for x in g)}; same page as owner save {same_page}')
pickle.dump(dict(saves=saves, borrowed=borrowed, owner=owner, own_ev=own_ev, inw={s['r']['rev_id'] for s in inw}),
            open(OUT + f'borrowed_{OWNER_DEF}{"_strict" if STRICT else ""}.pkl', 'wb'))
