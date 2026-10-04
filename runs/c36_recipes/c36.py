"""C36: copied where visible, or brought along? For each link recipe / page template / relay wording (common.RECIPES),
the unit is a label's FIRST eligible save whose added text matches the recipe.
Statistics per recipe (and pooled):
  page   the page's latest revision before the save (time < t) already showed the recipe in a line inserted by
         another label (line owners from common.line_owners)
  page10 the same, for any body standing on that page at some moment in the previous 10 minutes
  w10/w60  another label added the recipe anywhere on the wiki in the previous 10 / 60 minutes
  any60  page or w60
  first  the use is in the label's first eligible save anywhere (arrives with it)
  new    the page had no earlier revision
Nulls (n draws, per recipe): T = first-use times permuted among the recipe's units of the same UTC day, page and label
kept, page body and wiki exposure recomputed at the shuffled time; S = each unit gets the time of a random eligible save
of the same day (any label, any page). p = (1 + #null >= real) / (n + 1).
usage (repo root): REPO=. OUT=... python runs/c36_recipes/c36.py [--n 500] [--nohub] [--sample 20]
       -> $OUT/c36[_nohub].json, $OUT/c36_units[_nohub].parquet, $OUT/c36_sample[_nohub].txt"""
import argparse, json, os, random
from collections import defaultdict
import numpy as np
import polars as pl
from common import CRE, GROUP, HUB, RECIPES, line_owners, load_adds, load_revs, unit_saves

OUT = os.environ.get("OUT", "results/c36_recipes")
STATS = ["page", "page10", "w10", "w60", "any60"]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--nohub", action="store_true"); ap.add_argument("--sample", type=int, default=20)
    a = ap.parse_args(); os.makedirs(OUT, exist_ok=True); rng = np.random.default_rng(36); random.seed(36)
    revs, adds = load_revs(), load_adds()
    saves = unit_saves(revs, adds)
    first_save = dict(saves.group_by("label").agg(pl.col("rev").sort_by("s").first()).iter_rows())
    if a.nohub:
        saves = saves.filter(pl.col("page") != HUB)
    owners = line_owners(revs)
    # page state index (every revision)
    P = {}
    for (pg,), g in revs.group_by(["page"]):
        g = g.sort(["s", "seq"]); P[pg] = (g["s"].to_numpy(), g["rev"].to_list(), g["body"].to_list(), g["seq"].to_list())
    mlines = {}

    def seen(pg, t, k, lab, strict_rev=None):
        """recipe visible on page pg just before time t (or just before revision strict_rev), minus lab's own lines."""
        if pg not in P: return False, None
        s, rv, bd, sq = P[pg]
        i = (rv.index(strict_rev) - 1) if strict_rev else int(np.searchsorted(s, t, "left")) - 1
        if i < 0: return False, None
        key = (rv[i], k)
        if key not in mlines:
            mlines[key] = {o for x, o in owners[rv[i]] if CRE[k].search(x)}
        return bool(mlines[key] - {lab}), rv[i]

    def seen_recent(pg, t, k, lab, w=600):
        """recipe shown on page pg (by another label's line) by any body standing at some moment in [t-w, t)."""
        if pg not in P: return False
        s, rv = P[pg][0], P[pg][1]
        i1 = int(np.searchsorted(s, t, "left")) - 1; i0 = max(0, int(np.searchsorted(s, t - w, "left")) - 1)
        for i in range(i1, i0 - 1, -1):
            key = (rv[i], k)
            if key not in mlines: mlines[key] = {o for x, o in owners[rv[i]] if CRE[k].search(x)}
            if mlines[key] - {lab}: return True
        return False
    # wiki exposure index: per recipe, times of adds (any revision) and per-label times
    addm = adds.select("rev", "label", pl.col("time").dt.epoch("s").alias("s"), "text")
    expo = {}
    for k, c in CRE.items():
        x = addm.filter(pl.col("text").str.contains(RECIPES[k])).unique(["rev"]).sort("s")
        bl = defaultdict(list)
        for lab, s in x.select("label", "s").iter_rows(): bl[lab or ""].append(s)
        expo[k] = (x["s"].to_numpy(), {l: np.array(v) for l, v in bl.items()}, x["s"].min() if x.height else None)

    def exposed(k, t, lab, w):
        s, bl, _ = expo[k]
        tot = np.searchsorted(s, t, "left") - np.searchsorted(s, t - w, "left")
        mine = bl.get(lab)
        own_n = 0 if mine is None else np.searchsorted(mine, t, "left") - np.searchsorted(mine, t - w, "left")
        return tot - own_n > 0
    day_saves = defaultdict(list)
    for d, s in saves.select(pl.col("t").dt.strftime("%Y-%m-%d"), "s").iter_rows(): day_saves[d].append(s)
    day_saves = {d: np.array(v) for d, v in day_saves.items()}

    def evaluate(U, k, times):
        r = {s: 0 for s in STATS}
        for (lab, pg), t in zip(U, times):
            v = seen(pg, t, k, lab)[0]; w10 = exposed(k, t, lab, 600); w60 = exposed(k, t, lab, 3600)
            r["page"] += v; r["page10"] += seen_recent(pg, t, k, lab); r["w10"] += w10; r["w60"] += w60; r["any60"] += (v or w60)
        return r
    res, unit_rows, pooled_real, pooled_null = {}, [], defaultdict(int), {n: defaultdict(lambda: np.zeros(a.n)) for n in "TS"}
    for k, c in CRE.items():
        u = saves.filter(pl.col("added").str.contains(RECIPES[k])).sort("s").group_by("label", maintain_order=True).first()
        u = u.with_columns(pl.col("t").dt.strftime("%Y-%m-%d").alias("day")).sort("s")
        if u.height == 0: continue
        U = list(zip(u["label"], u["page"])); T0 = u["s"].to_numpy(); days = u["day"].to_list()
        real = {"page": 0, "page10": 0, "w10": 0, "w60": 0, "any60": 0, "page_strict": 0, "first": 0, "new": 0}
        for i, r in enumerate(u.iter_rows(named=True)):
            v, prev = seen(r["page"], r["s"], k, r["label"]); vs, _ = seen(r["page"], None, k, r["label"], strict_rev=r["rev"])
            w10, w60 = exposed(k, r["s"], r["label"], 600), exposed(k, r["s"], r["label"], 3600)
            fs = first_save.get(r["label"]) == r["rev"]; new = prev is None
            p10 = seen_recent(r["page"], r["s"], k, r["label"])
            for kk, vv in (("page", v), ("page10", p10), ("w10", w10), ("w60", w60), ("any60", v or w60), ("page_strict", vs), ("first", fs), ("new", new)):
                real[kk] += bool(vv)
            unit_rows.append({"recipe": k, "label": r["label"], "page": r["page"], "rev": r["rev"], "t": str(r["t"])[:19],
                              "rank": i, "page_vis": v, "page10": p10, "prev_rev": prev, "w10": w10, "w60": w60, "first_save": fs, "new_page": new,
                              "summary": r["summary"], "added": r["added"][:400]})
        idx = defaultdict(list)
        for i, d in enumerate(days): idx[d].append(i)
        nulls = {n: {s: np.zeros(a.n) for s in STATS} for n in "TS"}
        for it in range(a.n):
            tT = T0.copy(); tS = T0.copy()
            for d, ii in idx.items():
                tT[ii] = T0[rng.permutation(ii)]; tS[ii] = rng.choice(day_saves[d], len(ii))
            for n, tt in (("T", tT), ("S", tS)):
                e = evaluate(U, k, tt)
                for s in STATS: nulls[n][s][it] = e[s]; pooled_null[n][(GROUP[k], s)][it] += e[s]; pooled_null[n][("all", s)][it] += e[s]
        for s in STATS: pooled_real[(GROUP[k], s)] += real[s]; pooled_real[("all", s)] += real[s]
        out = {"group": GROUP[k], "units": u.height, "first_add": str(expo[k][2] and np.datetime64(int(expo[k][2]), "s")),
               "first_unit": {"label": u["label"][0], "t": str(u["t"][0])[:19], "rev": u["rev"][0], "page": u["page"][0]}, **real}
        for n in "TS":
            for s in STATS:
                z = nulls[n][s]; out[f"{n}_{s}"] = [round(float(z.mean()), 1), float(np.percentile(z, 95)),
                                                      round((1 + int((z >= real[s]).sum())) / (a.n + 1), 4)]
        res[k] = out
        print(f"{k:28s} n={u.height:4d} page {real['page']:4d} (T {out['T_page'][0]:6.1f} p{out['T_page'][2]:.3f} | S {out['S_page'][0]:6.1f})"
              f"  page10 {real['page10']:4d} (T {out['T_page10'][0]:6.1f} p{out['T_page10'][2]:.3f})"
              f"  w60 {real['w60']:4d} (T {out['T_w60'][0]:6.1f} p{out['T_w60'][2]:.3f} | S {out['S_w60'][0]:6.1f} p{out['S_w60'][2]:.3f})"
              f"  first {real['first']} new {real['new']}", flush=True)
    pooled = {}
    for (g, s), v in pooled_real.items():
        pooled[f"{g}:{s}"] = {"real": v, **{n: [round(float(pooled_null[n][(g, s)].mean()), 1), float(np.percentile(pooled_null[n][(g, s)], 95)),
                                              round((1 + int((pooled_null[n][(g, s)] >= v).sum())) / (a.n + 1), 4)] for n in "TS"}}
    for kk, v in sorted(pooled.items()): print("POOLED", kk, v)
    sfx = "_nohub" if a.nohub else ""
    json.dump({"recipes": res, "pooled": pooled, "n": a.n}, open(f"{OUT}/c36{sfx}.json", "w"), indent=1, default=str)
    ur = pl.DataFrame(unit_rows); ur.write_parquet(f"{OUT}/c36_units{sfx}.parquet")
    # reading sample: random first uses of the five biggest recipes, with the previous body's matching lines
    with open(f"{OUT}/c36_sample{sfx}.txt", "w") as f:
        big = ur.group_by("recipe").len().sort("len", descending=True).head(6)["recipe"].to_list()
        smp = ur.filter(pl.col("recipe").is_in(big)).sample(min(a.sample, ur.height), seed=36).sort("t")
        bodies = dict(revs.select("rev", "body").iter_rows())
        for r in smp.iter_rows(named=True):
            pb = bodies.get(r["prev_rev"], "") if r["prev_rev"] else ""
            ml = [x for x in pb.split("\n") if CRE[r["recipe"]].search(x)][:2]
            f.write(f"## {r['recipe']} | {r['rev']} | {r['t']} | {r['label']} | page_vis={r['page_vis']} w60={r['w60']} "
                    f"first_save={r['first_save']} new={r['new_page']} | summary={r['summary']!r}\n  ADDED: {r['added'][:300]!r}\n"
                    f"  PREV {r['prev_rev']}: {ml!r}\n")


if __name__ == "__main__":
    main()
