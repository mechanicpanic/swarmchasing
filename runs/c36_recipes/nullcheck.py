"""C36 null C (cold check): first-use times shuffled only to moments after the page existed, so the null does not count
page existence as visibility. usage: REPO=<repo root> python runs/c36_recipes/nullcheck.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, polars as pl
from collections import defaultdict
from common import CRE, RECIPES, line_owners, load_adds, load_revs, unit_saves
N = int(os.environ.get("N", "500")); rng = np.random.default_rng(99)
revs, adds = load_revs(), load_adds(); saves = unit_saves(revs, adds); owners = line_owners(revs)
P = {}
for (pg,), g in revs.group_by(["page"]):
    g = g.sort(["s", "seq"]); P[pg] = (g["s"].to_numpy(), g["rev"].to_list())
cache = {}
def vis(pg, t, k, lab):
    s, rv = P[pg]; i = int(np.searchsorted(s, t, "left")) - 1
    if i < 0: return False
    key = (rv[i], k)
    if key not in cache: cache[key] = {o for x, o in owners[rv[i]] if CRE[k].search(x)}
    return bool(cache[key] - {lab})
tot = defaultdict(lambda: [0, np.zeros(N), np.zeros(N)])  # real, T null, C null
for k in CRE:
    u = saves.filter(pl.col("added").str.contains(RECIPES[k])).sort("s").group_by("label", maintain_order=True).first().sort("s")
    if u.height == 0: continue
    lab = u["label"].to_list(); pg = u["page"].to_list(); T0 = u["s"].to_numpy()
    day = (T0 // 86400); birth = np.array([P[p][0][0] for p in pg])
    nonbirth = birth < T0  # page existed before the save (strictly earlier second)
    old = birth < day * 86400  # page born before the unit's UTC day
    real = np.array([vis(p, t, k, l) for p, t, l in zip(pg, T0, lab)])
    idx = defaultdict(list)
    for i, d in enumerate(day): idx[d].append(i)
    for it in range(N):
        tT = T0.copy()
        for d, ii in idx.items(): tT[ii] = T0[rng.permutation(ii)]
        vT = np.array([vis(p, t, k, l) for p, t, l in zip(pg, tT, lab)])
        # C: non-birth units get a same-day first-use time of this recipe at which the page already existed
        vC = np.zeros(len(T0), bool)
        for i in np.where(nonbirth)[0]:
            cand = T0[idx[day[i]]]; cand = cand[cand > birth[i]]
            vC[i] = vis(pg[i], rng.choice(cand), k, lab[i])
        for name, m in (("all", np.ones(len(T0), bool)), ("nonbirth", nonbirth), ("old_page", old)):
            for kk in (name, f"{k}|{name}"):
                tot[kk][1][it] += vT[m].sum(); tot[kk][2][it] += vC[m].sum()
    for name, m in (("all", np.ones(len(T0), bool)), ("nonbirth", nonbirth), ("old_page", old)):
        for kk in (name, f"{k}|{name}"): tot[kk][0] += int(real[m].sum())
def fmt(v):
    r, a, b = v
    return (f"real {r} | T mean {a.mean():.1f} sd {a.std():.1f} p95 {np.percentile(a,95):.0f} z {(r-a.mean())/max(a.std(),1e-9):.1f}"
            f" | C mean {b.mean():.1f} sd {b.std():.1f} p95 {np.percentile(b,95):.0f} z {(r-b.mean())/max(b.std(),1e-9):.1f}")
for kk in sorted(tot, key=lambda x: ("|" in x, x)): print(f"{kk:34s}", fmt(tot[kk]))
