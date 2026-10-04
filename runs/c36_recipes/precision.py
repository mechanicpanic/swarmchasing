"""C36 detector read sample: k random first-use units per recipe with the matching line of the added text, for reading
by hand (is the match really that recipe?). usage: REPO=. OUT=... python runs/c36_recipes/precision.py [--k 3]"""
import argparse, os
import polars as pl
from common import CRE

OUT = os.environ.get("OUT", "results/c36_recipes")
ap = argparse.ArgumentParser(); ap.add_argument("--k", type=int, default=3); a = ap.parse_args()
u = pl.read_parquet(f"{OUT}/c36_units.parquet")
for k, c in CRE.items():
    x = u.filter(pl.col("recipe") == k)
    for r in x.sample(min(a.k, x.height), seed=7).iter_rows(named=True):
        ln = next((l for l in r["added"].split("\n") if c.search(l)), r["added"])
        m = c.search(ln); s = max(0, (m.start() if m else 0) - 60)
        print(f"{k:24s} | {r['rev']:44s} | {r['label']:22s} | {ln[s:s + 170]!r}")
