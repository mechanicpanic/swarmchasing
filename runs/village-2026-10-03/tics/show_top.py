import sys, polars as pl
src = sys.argv[1]; kind = sys.argv[2] if len(sys.argv) > 2 else "agent"
r = pl.read_parquet(f"lo_{src}.parquet")
r = r.filter((pl.col("weeks") >= 5) & (pl.col("days") >= 8) & (pl.col("max_week_share") <= 0.3)
             & (pl.col("n") >= 2) & ~pl.col("g").str.contains(r"\d|urlx|emailx"))
for (k, u), g in r.sort("z", descending=True).group_by(["unit_kind", "unit"], maintain_order=True):
    if k != kind or u in ("GPT-5.6 Terra", "GPT-5.6 Luna"): continue
    g = g.head(int(sys.argv[3]) if len(sys.argv) > 3 else 30)
    print(f"## {u} (n={g['n_docs'][0]})")
    print("; ".join(f"{x} {y:.0f}/{b:.1f}" for x, y, b in zip(g["g"], g["rate_1k"], g["bg_1k"])))
