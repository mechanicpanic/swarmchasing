# Daily view + sample messages around a candidate change point.
# usage: peek.py "<agent>" YYYY-MM-DD feat1,feat2 [days=10] [samples=3] [regex]
# chat features come from msg_chat.parquet; if a regex is given, samples are
# drawn from messages matching it.
import sys, polars as pl, datetime as dt

OUT = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/leads-changepoints/"
CORP = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/"
agent, day, feats = sys.argv[1], dt.date.fromisoformat(sys.argv[2]), sys.argv[3].split(",")
days = int(sys.argv[4]) if len(sys.argv) > 4 else 10
ns = int(sys.argv[5]) if len(sys.argv) > 5 else 3
rx = sys.argv[6] if len(sys.argv) > 6 else None
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_width_chars(200)
m = pl.read_parquet(OUT + "msg_chat.parquet").filter(pl.col("agent") == agent)
m = m.with_columns(pl.col("time").dt.date().alias("day")).filter(
    (pl.col("day") >= day - dt.timedelta(days=days)) & (pl.col("day") <= day + dt.timedelta(days=days)))
feats = [f for f in feats if f in m.columns]
print(m.group_by("day").agg(pl.len().alias("n"), *[pl.col(f).cast(pl.Float64).mean().round(3) for f in feats]).sort("day"))
txt = pl.read_parquet(CORP + "chat.parquet", columns=["id", "text", "room"]).join(m.select("id", "time", "day"), on="id")
if rx: txt = txt.filter(pl.col("text").str.contains(rx))
for lab, sub in [("BEFORE", txt.filter(pl.col("day") < day)), ("AFTER", txt.filter(pl.col("day") >= day))]:
    print(f"--- {lab} ({sub.height})")
    for r in sub.sample(min(ns, sub.height), seed=1).sort("time").iter_rows(named=True):
        print(f"[{str(r['time'])[:16]} {r['room']}] {r['text'][:400]!r}")
