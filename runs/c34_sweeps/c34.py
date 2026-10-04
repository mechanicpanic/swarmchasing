"""C34: did the admin's deletion runs change where agents wrote? Loads via common.py (env REPO).
Unit (run, family): agent saves of the family on dse in the 24 h before the run's first delete vs the 24 h after
its last; family = the export's page_family. A family is hit when the run deletes one of its pages; units need >=1
save before. y = log((after+1)/(before+1)); statistic = mean y(hit) - mean y(not hit, same runs).
Nulls: 'fam' gives each family another family's whole hit schedule (keeps every family's activity series and every
run's hit count); 'strat' permutes hit flags within (run, before-saves bin), against "busy families get swept and
then cool down". Page level: each deleted page vs a non-deleted dse page drawn from the same recency bin (hours since
its last save) at the same moment. Venue share and global counts: all runs shifted together by a random circular
offset inside Jun 17 00:00 - Jun 21 09:20 (keeps their spacing).
usage: REPO=. python runs/c34_sweeps/c34.py [--n 1000] [--min-size 1] [--no-hub] [--hours 24] [--first-delete]"""
import argparse, bisect, math, random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import polars as pl
import common as C

ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=1000); ap.add_argument("--min-size", type=int, default=1)
ap.add_argument("--no-hub", action="store_true"); ap.add_argument("--hours", type=float, default=24)
ap.add_argument("--first-delete", action="store_true", help="page level: only the first delete of each page")
a = ap.parse_args(); W = timedelta(hours=a.hours)
S = C.saves(a.no_hub); D = C.deletions(); R = C.runs(D, a.min_size)
dse = S.filter(pl.col("wiki") == "dse")
first = S.group_by("page").agg(pl.col("time").min()).rename({"time": "t0"})  # a page's first save = its creation
print(f"runs {R.height} (>= {a.min_size} deletes, after-window closes before the stop), deletes {R['n'].sum()}, window {a.hours} h, hub {'out' if a.no_hub else 'in'}")
print(R.select("run", "start", "end", "n", pl.col("fams").list.len().alias("families")))
def pct(xs, v):
    xs = sorted(xs); n = len(xs)
    return f"null mean {sum(xs)/n:+.3f} 5th {xs[int(.05*n)]:+.3f} 95th {xs[int(.95*n)-1]:+.3f}  p(>=) {sum(x >= v for x in xs)/n:.3f}  p(<=) {sum(x <= v for x in xs)/n:.3f}"

# ---- family units ----
ft = defaultdict(list); fn = defaultdict(list)
for f, t in dse.filter(pl.col("page_family").is_not_null()).select("page_family", "time").iter_rows(): ft[f].append(t)
for f, t in dse.join(first, on="page").filter((pl.col("time") == pl.col("t0")) & pl.col("page_family").is_not_null()).select("page_family", "time").iter_rows(): fn[f].append(t)
fams = sorted(ft); runs = list(R.select("start", "end", "fams").iter_rows())
U = []  # (run index, family, y_saves, y_new, before, after)
for i, (s, e, _) in enumerate(runs):
    for f in fams:
        b, af = C.count_in(ft[f], s - W, s), C.count_in(ft[f], e, e + W)
        if b: U.append((i, f, math.log((af + 1) / (b + 1)), math.log((C.count_in(fn[f], e, e + W) + 1) / (C.count_in(fn[f], s - W, s) + 1)), b, af))
def stat(hit, k):
    h = [u[k] for u, x in zip(U, hit) if x]; c = [u[k] for u, x in zip(U, hit) if not x]
    return sum(h) / len(h) - sum(c) / len(c) if h and c else 0.0
sched = {f: {i for i, (_, _, fs) in enumerate(runs) if f in fs} for f in fams}
real = [u[1] in runs[u[0]][2] for u in U]
nh = sum(real); print(f"\nfamily units {len(U)} ({nh} hit, {len(U)-nh} not hit)")
for k, name in ((2, "saves"), (3, "new pages")):
    h = [u for u, x in zip(U, real) if x]; c = [u for u, x in zip(U, real) if not x]
    if k == 2: print(f"  pooled saves before->after: hit {sum(u[4] for u in h)}->{sum(u[5] for u in h)}   not hit {sum(u[4] for u in c)}->{sum(u[5] for u in c)}")
    v = stat(real, k); nf, ns = [], []
    bins = [min(3, int(math.log10(u[4]) + 0.3)) for u in U]
    for j in range(a.n):
        rng = random.Random(j); perm = fams[:]; rng.shuffle(perm); m = dict(zip(fams, perm))
        nf.append(stat([u[0] in sched[m[u[1]]] for u in U], k))
        grp = defaultdict(list)
        for idx, u in enumerate(U): grp[(u[0], bins[idx])].append(idx)
        hit = real[:]
        for idxs in grp.values():
            fl = [real[x] for x in idxs]; rng.shuffle(fl)
            for x, v2 in zip(idxs, fl): hit[x] = v2
        ns.append(stat(hit, k))
    print(f"  {name}: mean log-ratio hit {sum(u[k] for u in h)/len(h):+.3f}  not hit {sum(u[k] for u in c)/len(c):+.3f}  diff {v:+.3f}")
    print(f"     fam   {pct(nf, v)}\n     strat {pct(ns, v)}")

# ---- labels: writers of hit families before vs writers of other families only ----
def fkey(w, f): return f if w == "dse" and f else f"{w}:{f or 'none'}"
L = [(lab, fkey(w, f), t) for lab, w, f, t in S.select("label", "wiki", "page_family", "time").iter_rows()]
LU = []  # (run, families written before, wrote after at all, wrote after on a family not written before)
for i, (s, e, _) in enumerate(runs):
    bef, aft = defaultdict(set), defaultdict(set)
    for lab, k, t in L:
        if s - W <= t < s: bef[lab].add(k)
        elif e <= t < e + W: aft[lab].add(k)
    for lab, ks in bef.items(): LU.append((i, ks, bool(aft[lab]), bool(aft[lab] - ks)))
def lstat(hitsets, k):
    h = [u[k] for u in LU if u[1] & hitsets[u[0]]]; c = [u[k] for u in LU if not u[1] & hitsets[u[0]]]
    return sum(h) / len(h) - sum(c) / len(c), len(h), len(c), sum(h) / len(h), sum(c) / len(c)
realsets = [set(fs) for _, _, fs in runs]
print(f"\nlabel-run units {len(LU)}")
for k, name in ((2, "writes again within window"), (3, "writes on a family/venue it did not use before")):
    v, nh_, nc_, sh, sc = lstat(realsets, k); null = []
    for j in range(a.n):
        rng = random.Random(j); perm = fams[:]; rng.shuffle(perm); m = dict(zip(perm, fams))  # family m[g] takes g's schedule
        null.append(lstat([{m[g] for g in fams if g in rs} for rs in realsets], k)[0])
    print(f"  {name}: hit {sh:.3f} (n {nh_})  not hit {sc:.3f} (n {nc_})  diff {v:+.3f}   fam {pct(null, v)}")

# ---- page level: deleted pages vs matched non-deleted pages ----
dele = D.filter(pl.col("run").is_in(R["run"].to_list())).select("page", "time")
if a.first_delete: dele = dele.sort("time").unique("page", keep="first", maintain_order=True)
deltimes = defaultdict(list)
for p, t in D.select("page", "time").iter_rows(): deltimes[p].append(t)
pt = defaultdict(list); pl_ = defaultdict(list)
for p, t, lab in dse.select("page", "time", "label").iter_rows(): pt[p].append(t); pl_[p].append(lab)
lt = defaultdict(list)
for lab, p, t in S.select("label", "page", "time").iter_rows(): lt[lab].append((t, p))
EDGES = [2 / 60, 5 / 60, 15 / 60, 1, 3, 6, 24, 72, 1e9]  # hours; minute bins (cold check: hour bins inflate the 10-min re-save excess)
def rbin(p, t):  # (hours since the last save, saves in the 24 h before), binned
    j = bisect.bisect_left(pt[p], t)
    if j == 0: return None
    n = j - bisect.bisect_left(pt[p], t - C.DAY)
    return next(k for k, x in enumerate(EDGES) if (t - pt[p][j - 1]).total_seconds() / 3600 < x), next(k for k, x in enumerate([1, 2, 5, 20, 1e9]) if n < x)
def outcome(p, t):  # (saved again within W, saved again within 10 min, an earlier author writes another page within W)
    j0, j1 = bisect.bisect_left(pt[p], t), bisect.bisect_left(pt[p], t + W)
    rep = j1 > j0 and pt[p][j0] - t < timedelta(minutes=10)
    auth = {pl_[p][x] for x in range(bisect.bisect_left(pt[p], t - W), j0)}
    moved = any(q != p for lab in auth for (tt, q) in lt[lab] if t < tt < t + W)
    return j1 > j0, rep, moved, bool(auth)
pages = sorted(pt); obs = []; pool = defaultdict(list)
for p, t in dele.iter_rows():
    b = rbin(p, t)
    if b is None: continue
    cands = [q for q in pages if rbin(q, t) == b and not any(t - timedelta(days=30) <= x <= t + W for x in deltimes.get(q, []))]
    if cands: obs.append(outcome(p, t)); pool[len(obs) - 1] = (cands, t)
print(f"\ndeleted pages with an earlier agent save and a matched pool: {len(obs)}")
nulls = [[], [], []]
for j in range(a.n):
    rng = random.Random(j); o = [outcome(rng.choice(c), t) for c, t in pool.values()]
    nulls[0].append(sum(x[0] for x in o)); nulls[1].append(sum(x[1] for x in o)); nulls[2].append(sum(x[2] for x in o if x[3]) / max(1, sum(x[3] for x in o)))
v = [sum(x[0] for x in obs), sum(x[1] for x in obs), sum(x[2] for x in obs if x[3]) / max(1, sum(x[3] for x in obs))]
for k, name in enumerate(["pages saved again within window", "pages saved again within 10 minutes", "share of pages whose earlier authors write another page"]):
    print(f"  {name}: {v[k]:.3f}   {pct(nulls[k], v[k])}")

# ---- venue share and global counts: runs shifted together ----
oth_ex, comm = C.explorer()
tdse = sorted(dse["time"].to_list()); toth = sorted(S.filter(pl.col("wiki").is_in(C.OTHER))["time"].to_list() + oth_ex["time"].to_list())
tnew = sorted(first.join(S.select("page", "wiki").unique("page"), on="page").filter(pl.col("wiki") == "dse")["t0"].to_list())
AW = r"(?i)clean-?up|mass-?clean|deletion|\b(was|were|got|been|being) (deleted|wiped|purged)|page (vanish|disappear)|archive survives|archive has"
aw = sorted(pl.read_parquet(f"{C.REPO}/data/wiki_msgs.parquet").filter((pl.col("kind") == "add") & pl.col("text").str.contains(AW) & ~pl.col("text").str.contains("(?i)safe to delete") & ~pl.col("text").str.contains("(?i)terminal exec cleanup|deadline cleanup|container cleanup|episode/container|merely cleanup"))["time"].to_list())
LO, HI = datetime(2026, 6, 17, tzinfo=timezone.utc), C.STOP - W
def vstat(sh):
    dd = []; ng = 0; na = set()
    for s, e, _ in runs:
        s2 = LO + (s - LO + sh) % (HI - LO); e2 = s2 + (e - s)
        sb = (C.count_in(toth, s2 - W, s2), C.count_in(tdse, s2 - W, s2)); sa = (C.count_in(toth, e2, e2 + W), C.count_in(tdse, e2, e2 + W))
        dd.append(sa[0] / max(1, sum(sa)) - sb[0] / max(1, sum(sb)))
        ng += C.count_in(tnew, e2, e2 + W) - C.count_in(tnew, s2 - W, s2); na |= {t for t in aw if e2 <= t < e2 + W}
    return sum(dd) / len(dd), ng, len(na)
v = vstat(timedelta(0)); null = [vstat(timedelta(seconds=random.Random(j).uniform(0, (HI - LO).total_seconds()))) for j in range(a.n)]
print(f"\nshifted-runs null (offset uniform over {LO:%b %d} - {HI:%b %d %H:%M})")
for k, name in enumerate(["other-venue share, after minus before (mean over runs)", "dse new pages after minus before (summed over runs; windows overlap)", "deletion-aware saves inside any after window (distinct; descriptive)"]):
    print(f"  {name}: {v[k]:+.3f}   {pct([x[k] for x in null], v[k])}")
print(f"community-found explorer rows (unverified, not in the share) within Jun 18-22: {comm.filter(pl.col('time').dt.date().is_between(datetime(2026,6,18).date(), datetime(2026,6,22).date())).height}")
