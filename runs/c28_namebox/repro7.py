"""Port of PR #7 signatures_slot.py rates (T1/T2/T3, W=10 min, nullA day-shuffle, nullB random active label) on our rows."""
import collections, pickle, random, statistics
OUT = __import__('os').environ.get('OUT', 'results/c28/')
rows = pickle.load(open(OUT + 'rows.pkl', 'rb'))
saves = []
for r in rows:
    new = [s for s in r['sigs'] if s['fresh'] == 'new']
    if new:
        names = [s['name'] for s in new]
        saves.append(dict(r=r, names=names, L=r['label'], match=r['label'] in names, last=new[-1]['name']))
mis = [s for s in saves if not s['match'] and s['L']]
lab_ev = collections.defaultdict(list); sig_ev = collections.defaultdict(list)
for r in rows: lab_ev[r['label']].append((r['t'], r['ip16'], r['rev_id']))
for s in saves:
    for nme in set(s['names']): sig_ev[nme].append((s['r']['t'], s['r']['rev_id']))
hour_labels = collections.defaultdict(list)
for r in rows:
    if r['label']: hour_labels[int(r['t'] // 3600)].append(r['label'])
T1 = lambda L, t, rid, W: any(t - W <= tt < t and rr != rid for tt, rr in sig_ev.get(L, []))
T3 = lambda L, t, rid, W: any(t - W <= tt < t and rr != rid for tt, ii, rr in lab_ev.get(L, []))
def rates(items, W=600):
    return (sum(T1(L, t, rid, W) for L, t, ip, rid in items) / len(items), sum(T3(L, t, rid, W) for L, t, ip, rid in items) / len(items))
def day_shuffle(items, rng):
    byday = collections.defaultdict(list)
    for i, it in enumerate(items): byday[int(it[1] // 86400)].append(i)
    out = list(items)
    for idx in byday.values():
        ts = [items[i][1] for i in idx]; rng.shuffle(ts)
        for i, t in zip(idx, ts): out[i] = (items[i][0], t, items[i][2], items[i][3])
    return out
def rand_label(items, rng):
    out = []
    for L, t, ip, rid in items:
        pool = [x for x in hour_labels[int(t // 3600)] if x != L]
        out.append((rng.choice(pool) if pool else L, t, ip, rid))
    return out
items = [(s['L'], s['r']['t'], s['r']['ip16'], s['r']['rev_id']) for s in mis]
real = rates(items); rng = random.Random(1)
nA = [rates(day_shuffle(items, rng)) for _ in range(200)]; nB = [rates(rand_label(items, rng)) for _ in range(200)]
for k, nm in enumerate(['T1 L signed another save in prior 10 min', 'T3 L saved at all in prior 10 min']):
    a = sorted(x[k] for x in nA); b = sorted(x[k] for x in nB)
    print(f'{nm}: n={len(items)} real {real[k]:.3f} | A day-shuffle median {statistics.median(a):.3f} 95th {a[189]:.3f} | B random same-hour label median {statistics.median(b):.3f} 95th {b[189]:.3f}')
own = {s['L'] for s in saves if s['match']}
print('mismatches whose label ever self-signs', sum(L in own for L, *_ in items))
