"""C30 (report §15): reaction to having one's text removed, signers vs non-signers. base.py builds events (run from
the repo root); lines.py N is the primary line-level test with whole-save nulls; ident.py N the identity-free variants;
dic.py the norm/apology dictionary. Env: REPO (repo root), OUT (outputs, default results/c30/)."""
"""C30, line-level variant: authorship and removal computed from revision bodies line by line (ASCII letters/digits
only, so re-encoding damage is not a removal), not from hunk text_keys.
Event = (rev, A): B's save removes >=1 line whose latest earlier adder on that page is A != B; whole-page removals
(every base line removed) excluded. Reaction = A's save within 30 min after it that re-adds one of those lines on the
page (re_line) or adds dictionary text anywhere (dic). Null: whole saves' times permuted within (day, page), only A's
saves after the removal are candidates.  usage: cd c30 && python lines.py N_NULL"""
import gzip, json, re, sys
from datetime import datetime
from collections import defaultdict
import numpy as np
import polars as pl
from dic import DIC

N = int(sys.argv[1]) if len(sys.argv) > 1 else 500
W = 1800
rng = np.random.default_rng(31)
grp = dict(pl.read_parquet("base_groups.parquet").iter_rows())
DICRX = re.compile(DIC)


def asc(t):
    return re.sub(r"[^a-z0-9]", "", t.encode("ascii", "ignore").decode().lower())


revs = [json.loads(l) for l in gzip.open(__import__("os").path.join(__import__("os").environ.get("REPO", "."), "data/collusion_wiki/revisions.jsonl.gz"), "rt")]
body = {r["rev_id"]: r.get("body") or "" for r in revs}
revs.sort(key=lambda r: (r["time"], r["page_key"], int(r["seq"])))
author = defaultdict(dict)  # page -> asc line -> latest adder
S, EV = [], []
for r in revs:
    new = body[r["rev_id"]].split("\n"); base = body.get(r.get("diff_base"), "").split("\n") if r.get("diff_base") not in (None, "None") else []
    na = {asc(x): x for x in new if len(asc(x)) >= 15}; ba = {asc(x): x for x in base if len(asc(x)) >= 15}
    added = {k: v for k, v in na.items() if k not in ba}; removed = [k for k in ba if k not in na]
    lab, p = r.get("label"), r["page_key"]
    t = datetime.fromisoformat(r["time"].replace("Z", "+00:00"))
    S.append(dict(rev=r["rev_id"], label=lab, page=p, time=t, lines=set(added), dic=bool(DICRX.search("\n".join(added.values())))))
    whole = bool(ba) and len(removed) == len(ba)
    if removed and lab:
        byA = defaultdict(list)
        for k in removed:
            a = author[p].get(k)
            if a and a != lab:
                byA[a].append(k)
        for a, ks in byA.items():
            EV.append(dict(rev=r["rev_id"], time=t, page=p, A=a, B=lab, lines=ks, whole=whole, n_base=len(ba),
                           rtext="\n".join(ba[k] for k in ks)))
    for k in added:
        author[p][k] = lab

sv = pl.DataFrame([{k: v for k, v in s.items() if k != "lines"} for s in S]).with_columns(
    pl.col("time").dt.date().alias("day"), pl.col("time").dt.epoch("s").alias("ts"))
slines = [s["lines"] for s in S]
ev = pl.DataFrame([{k: v for k, v in e.items() if k != "lines"} for e in EV]).with_columns(
    pl.Series("lines", [e["lines"] for e in EV]), pl.col("time").dt.epoch("s").alias("ts"))
print("by-other line removals (rev, A):", ev.height, "| whole-page:", ev["whole"].sum(), "| remover is an admin:",
      ev["B"].str.starts_with("[").sum())
ev = ev.filter(~pl.col("whole")).with_columns(
    pl.col("A").replace_strict(grp, default=False).alias("signer"),
    (pl.col("page") == "dse~WillkommenImWiki").alias("hub"), (pl.col("time").dt.date() == pl.date(2026, 6, 18)).alias("j18"))
print("message-level events:", ev.height, "| A labels:", ev["A"].n_unique(), "| signer events:", ev["signer"].sum(),
      "| signer A labels:", ev.filter("signer")["A"].n_unique())

lab = sv["label"].to_list(); page = sv["page"].to_list(); dic = sv["dic"].to_numpy(); ts0 = sv["ts"].to_numpy()
by_lab = defaultdict(list)
for i, l in enumerate(lab):
    by_lab[l].append(i)
cells = defaultdict(list)
for i, (d, p) in enumerate(zip(sv["day"].to_list(), page)):
    cells[(d, p)].append(i)
cells = [np.array(v) for v in cells.values() if len(v) > 1]
E = [(A, t, p, set(ls)) for A, t, p, ls in ev.select("A", "ts", "page", "lines").iter_rows()]


def react(ts):
    out = np.zeros((len(E), 4), bool)
    for j, (A, t, p, ls) in enumerate(E):
        idx = [i for i in by_lab.get(A, []) if ts0[i] > t and t < ts[i] <= t + W]
        if not idx:
            continue
        rl = any(page[i] == p and slines[i] & ls for i in idx)
        dc = any(dic[i] for i in idx)
        f = min(idx, key=lambda i: ts[i])
        out[j] = (rl, dc, rl or dc, (page[f] == p and bool(slines[f] & ls)) or bool(dic[f]))
    return out


real = react(ts0)


def _shuffle():
    ts = ts0.copy()
    for c in cells:
        ts[c] = ts0[rng.permutation(c)]
    return ts


nulls = np.stack([react(_shuffle()) for _ in range(N)])
TYPES = ["re_line", "dic", "any", "first"]
ev = ev.with_columns(*[pl.Series(n, real[:, k]) for k, n in enumerate(TYPES)])
ev.drop("lines").write_parquet("events_lines.parquet")


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0, (c - h) / d), (c + h) / d)


hub = ev["hub"].to_numpy(); j18 = ev["j18"].to_numpy(); sg = ev["signer"].to_numpy(); Al = np.array(ev["A"].to_list())
for sname, m in {"all": np.ones(len(E), bool), "no hub": ~hub, "no Jun18": ~j18, "no hub, no Jun18": ~hub & ~j18}.items():
    print(f"\n## subset: {sname}  (events {m.sum()})")
    for gname, g in (("signers", sg), ("non-signers", ~sg)):
        mm = m & g; n = mm.sum()
        print(f"  {gname}: events {n}, A labels {len(set(Al[mm]))}")
        for k, t in enumerate(TYPES):
            x = real[mm, k].sum(); nd = nulls[:, mm, k].sum(1); lo, hi = wilson(x, n)
            print(f"    {t:7s} real {x:4d} ({x/max(n,1):.3f}, CI {lo:.3f}-{hi:.3f})  null med {np.median(nd):6.1f} 95th "
                  f"{np.percentile(nd,95):6.1f} max {nd.max():4d}  p={(1+(nd>=x).sum())/(N+1):.3f}")
    k = 2; y = real[m, k].astype(float); a = Al[m]; s = sg[m]
    if s.any() and (~s).any():
        labs = np.unique(a); ls_ = {l: s[a == l][0] for l in labs}; lv = np.array([ls_[l] for l in labs])
        pos = {l: i for i, l in enumerate(labs)}; ai = np.array([pos[l] for l in a])
        ex = y - nulls[:, m, k].mean(0)
        diff = y[s].mean() - y[~s].mean(); exd = ex[s].mean() - ex[~s].mean()
        pd, pe, bs = [], [], []
        for _ in range(2000):
            sp = rng.permutation(lv)[ai]
            pd.append(y[sp].mean() - y[~sp].mean()); pe.append(ex[sp].mean() - ex[~sp].mean())
            pick = rng.choice(len(labs), len(labs)); ii = np.concatenate([np.where(ai == q)[0] for q in pick]); ss = s[ii]
            if ss.any() and (~ss).any():
                bs.append(y[ii][ss].mean() - y[ii][~ss].mean())
        pd, pe = np.array(pd), np.array(pe)
        print(f"  compare any: rate diff (signers - non) {diff:+.3f}, label-cluster bootstrap 95% CI {np.percentile(bs,2.5):+.3f}.."
              f"{np.percentile(bs,97.5):+.3f}, label-permutation p={(np.abs(pd)>=abs(diff)).mean():.3f}; excess over null "
              f"{ex[s].mean():+.3f} vs {ex[~s].mean():+.3f}, diff perm p={(np.abs(pe)>=abs(exd)).mean():.3f}")

g2 = sv.with_columns(pl.col("label").replace_strict(grp, default=None).alias("signer")).filter(pl.col("signer").is_not_null())
print("\n## dictionary base rate in saves (line-level added text)")
print(g2.group_by("signer").agg(pl.len().alias("saves"), pl.col("dic").sum().alias("dic_saves"), pl.col("dic").mean().alias("rate")))
