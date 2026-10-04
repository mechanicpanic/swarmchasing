import pickle, collections, random, statistics

OUT = './out/'  # intermediates
rows = pickle.load(open(OUT + 'rows.pkl', 'rb'))
saves, mis, ex = pickle.load(open(OUT + 'mis.pkl', 'rb'))
mis = [s for s in mis if s['L']]  # drop blank-label saves

lab_ev = collections.defaultdict(list)   # label -> [(t, ip16, rev_id)]
for r in rows:
    lab_ev[r['label']].append((r['t'], r['ip16'], r['rev_id']))
sig_ev = collections.defaultdict(list)   # sig -> [(t, rev_id)]
for s in saves:
    for n in set(s['names']):
        sig_ev[n].append((s['r']['t'], s['r']['rev_id']))
for d in (lab_ev, sig_ev):
    for v in d.values():
        v.sort()
hour_labels = collections.defaultdict(list)
for r in rows:
    if r['label']:
        hour_labels[int(r['t'] // 3600)].append(r['label'])


def T1(L, t, rid, W):  # L signed some other save in previous W
    return any(t - W <= tt < t and rr != rid for tt, rr in sig_ev.get(L, []))


def T2(L, t, ip, rid, W):  # L saved from same ip16 in previous W
    return any(t - W <= tt < t and ii == ip and rr != rid for tt, ii, rr in lab_ev.get(L, []))


def T3(L, t, rid, W):  # L saved at all in previous W
    return any(t - W <= tt < t and rr != rid for tt, ii, rr in lab_ev.get(L, []))


def rates(items, W):
    n = len(items)
    a = sum(T1(L, t, rid, W) for L, t, ip, rid in items) / n
    b = sum(T2(L, t, ip, rid, W) for L, t, ip, rid in items) / n
    c = sum(T3(L, t, rid, W) for L, t, ip, rid in items) / n
    return a, b, c


def day_shuffle(items, rng):
    byday = collections.defaultdict(list)
    for i, it in enumerate(items):
        byday[int(it[1] // 86400)].append(i)
    out = list(items)
    for idx in byday.values():
        ts = [items[i][1] for i in idx]
        rng.shuffle(ts)
        for i, t in zip(idx, ts):
            L, _, ip, rid = items[i]
            out[i] = (L, t, ip, rid)
    return out


def rand_label(items, rng):
    out = []
    for L, t, ip, rid in items:
        pool = [x for x in hour_labels[int(t // 3600)] if x != L]
        out.append((rng.choice(pool) if pool else L, t, ip, rid))
    return out


items = [(s['L'], s['r']['t'], s['r']['ip16'], s['r']['rev_id']) for s in mis]
items_m = [(s['L'], s['r']['t'], s['r']['ip16'], s['r']['rev_id']) for s in saves if s['match']]
# alternative: the SIGNER's name instead of label (does the signer have its own recent activity?)
items_sig = [(s['last'], s['r']['t'], s['r']['ip16'], s['r']['rev_id']) for s in mis]
NREP = 200
for W in (600, 1800, 3600):
    real = rates(items, W)
    rng = random.Random(1)
    nullA = [rates(day_shuffle(items, rng), W) for _ in range(NREP)]
    nullB = [rates(rand_label(items, rng), W) for _ in range(NREP)]
    def summ(nl, k):
        v = sorted(x[k] for x in nl)
        return f'{statistics.median(v):.3f} [95th {v[int(.95*len(v))-1]:.3f}]'
    print(f'W={W//60}min  n_mis={len(items)}')
    for k, name in enumerate(['T1 L signed other save', 'T2 L saved same ip16', 'T3 L saved any ip16']):
        print(f'   {name}: real {real[k]:.3f} | nullA day-shuffle {summ(nullA, k)} | nullB random active label {summ(nullB, k)}')
    rm = rates(items_m, W)
    print(f'   matched saves comparator: T1 {rm[0]:.3f} T2 {rm[1]:.3f} T3 {rm[2]:.3f}')
    rs = rates(items_sig, W)
    print(f'   signer-name in mismatches: T1 {rs[0]:.3f} T2 {rs[1]:.3f} T3(signer saved under own label) {rs[2]:.3f}')

# crossed pairs: a save labelled s signed L within +-W
W = 1800
cross = 0
for s in mis:
    L, sig, t = s['L'], s['last'], s['r']['t']
    for o in saves:
        if o['L'] == sig and L in o['names'] and abs(o['r']['t'] - t) <= W:
            cross += 1; break
print('crossed label/sig swaps within 30min', cross, 'of', len(mis))

# ---- inheritance timing: label owner = signs as L under label L
own = collections.defaultdict(list)
for s in saves:
    if s['match']:
        own[s['L']].append(s['r']['t'])
pos = collections.Counter(); gaps = []
for s in mis:
    L, t = s['L'], s['r']['t']
    if L not in own:
        pos['L never self-signs'] += 1
        continue
    ts = own[L]
    if t < min(ts):
        pos['before owner first self-signed'] += 1
    elif t > max(ts):
        pos['after owner last self-signed'] += 1; gaps.append((t - max(ts)) / 60)
    else:
        pos['within owner span'] += 1
print('mismatch position vs label-owner span', pos)
if gaps:
    gs = sorted(gaps); print('   gap after owner (min): median', round(statistics.median(gs)), 'p25', round(gs[len(gs)//4]), 'p75', round(gs[3*len(gs)//4]))

# null for position: shuffle times within day
rng = random.Random(2)
cnts = []
for _ in range(200):
    sh = day_shuffle(items, rng); c = collections.Counter()
    for L, t, ip, rid in sh:
        if L not in own: continue
        ts = own[L]
        c['before' if t < min(ts) else 'after' if t > max(ts) else 'within'] += 1
    cnts.append(c)
for k in ('before', 'within', 'after'):
    v = sorted(c[k] for c in cnts); print('   null', k, statistics.median(v), 'p5-p95', v[10], v[189])
