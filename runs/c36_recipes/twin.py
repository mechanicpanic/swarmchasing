"""C36 twin: the June 16 'SequenceCollab' relay-page births. Is each new collab page worded like the previous collab page
(copied from what was just visible) more than like other pages born in the same hour (same time, no relay format)?
Births = first revision of each page; collab = page name contains 'SequenceCollab'; 2026-06-16 UTC.
Similarity = Jaccard of word 3-gram shingles (lower case, digits -> #, wiki links and URLs removed); word-set Jaccard
as a variant. Comparison per collab birth i >= 2: sim(i, previous collab birth) vs sim(i, every non-collab birth within
+-30 min of i); also sim(i, previous) vs sim(i, earlier non-adjacent collab births).
Null: label permutation of which earlier birth counts as 'previous collab' among the collab + same-window births (n).
usage (repo root): REPO=. python runs/c36_recipes/twin.py [--n 2000]"""
import argparse, re
import numpy as np
import polars as pl
from common import load_revs

DAY, KEY = "2026-06-16", "SequenceCollab"


def toks(b):
    b = re.sub(r"https?://\S+|\[[^\]]*\]", " ", b or "").lower()
    return re.findall(r"[a-z#]+", re.sub(r"\d+", "#", b))


def sh(b, k=3):
    t = toks(b); return {tuple(t[i:i + k]) for i in range(max(0, len(t) - k + 1))}


def jac(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=2000); a = ap.parse_args()
    rng = np.random.default_rng(36)
    revs = load_revs()
    births = revs.sort(["s", "seq"]).group_by("page", maintain_order=True).first()
    births = births.filter(pl.col("t").dt.strftime("%Y-%m-%d") == DAY).with_columns(pl.col("page").str.contains(KEY).alias("collab")).sort("s")
    B = births.to_dicts()
    for b in B: b["sh"], b["ws"] = sh(b["body"]), set(toks(b["body"]))
    col = [b for b in B if b["collab"]]
    print(f"births on {DAY}: {len(B)}; collab births: {len(col)}; first {col[0]['page']} {str(col[0]['t'])[:19]} {col[0]['label']}")
    rows = []
    for i in range(1, len(col)):
        c, p = col[i], col[i - 1]
        oth = [b for b in B if not b["collab"] and abs(b["s"] - c["s"]) <= 1800 and b["label"] != c["label"]]
        older = [col[j] for j in range(i - 1)]
        for kind in ("sh", "ws"):
            rows.append({"i": i, "page": c["page"], "label": c["label"], "t": str(c["t"])[11:19], "kind": kind,
                         "prev": jac(c[kind], p[kind]), "oth_med": float(np.median([jac(c[kind], o[kind]) for o in oth])) if oth else None,
                         "oth_max": max([jac(c[kind], o[kind]) for o in oth], default=None), "n_oth": len(oth),
                         "older_med": float(np.median([jac(c[kind], o[kind]) for o in older])) if older else None,
                         "same_label_prev": c["label"] == p["label"], "gap_s": c["s"] - p["s"]})
    d = pl.DataFrame(rows)
    pl.Config.set_tbl_rows(80); pl.Config.set_tbl_width_chars(250)
    for kind in ("sh", "ws"):
        x = d.filter(pl.col("kind") == kind)
        print(f"\n== {kind}: per collab birth")
        print(x.select("i", "t", "page", "label", "gap_s", pl.col("prev").round(3), pl.col("oth_med").round(3), pl.col("oth_max").round(3),
                       "n_oth", pl.col("older_med").round(3)))
        v = x.drop_nulls("oth_med")
        diff = (v["prev"] - v["oth_med"]).to_numpy(); dmax = (v["prev"] > v["oth_max"]).sum()
        # sign-flip null on the paired difference prev - other-births median
        null = np.array([np.mean(diff * rng.choice([-1, 1], len(diff))) for _ in range(a.n)])
        p = (1 + (null >= diff.mean()).sum()) / (a.n + 1)
        print(f"{kind}: n={len(v)}  median prev={np.median(v['prev']):.3f}  median other-births={np.median(v['oth_med']):.3f}  "
              f"prev > every other birth: {dmax}/{len(v)}  mean diff={diff.mean():.3f} sign-flip p={p:.4f}")
        w = x.drop_nulls("older_med"); dd = (w["prev"] - w["older_med"]).to_numpy()
        null = np.array([np.mean(dd * rng.choice([-1, 1], len(dd))) for _ in range(a.n)])
        print(f"{kind}: previous collab vs older collab pages: median prev={np.median(w['prev']):.3f} older={np.median(w['older_med']):.3f} "
              f"mean diff={dd.mean():.3f} p={(1 + (null >= dd.mean()).sum()) / (a.n + 1):.4f}")


if __name__ == "__main__":
    main()
