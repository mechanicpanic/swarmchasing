# Run time-matched log-odds for every agent and every family/lab/cohort.
# Output: lo_<src>_<unitkind>.parquet with top grams per unit.
import sys, polars as pl
from stats import load, meta, logodds, prune_subsumed
src = sys.argv[1]
c, v, d = load(src)
c = c.with_columns(pl.col("agent").cast(pl.Categorical))
d = d.with_columns(pl.col("agent").cast(pl.Categorical))
m = meta()
units = [("agent", a, [a]) for a in m["agent"].to_list()]
for col in ["family", "lab", "cohort"]:
    for val in m[col].drop_nulls().unique().to_list():
        units.append((col, val, m.filter(pl.col(col) == val)["agent"].to_list()))
res = []
for kind, name, mem in units:
    mem = [x for x in mem if x in set(d["agent"].cast(pl.String).unique().to_list())]
    if not mem: continue
    out, nU = logodds(c, d, mem, min_y=8)
    if out.height == 0: continue
    top = out.filter(pl.col("z") > 3).sort("z", descending=True).head(400)
    top = prune_subsumed(top, v)
    res.append(top.with_columns(unit_kind=pl.lit(kind), unit=pl.lit(name), n_docs=pl.lit(nU),
                                n_members=pl.lit(len(mem))))
    print(kind, name, nU, top.height, flush=True)
pl.concat(res, how="diagonal").write_parquet(f"lo_{src}.parquet")
