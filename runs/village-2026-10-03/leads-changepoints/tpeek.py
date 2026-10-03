# Thought rows around a date for one agent, optionally filtered by regex.
# usage: tpeek.py "<agent>" YYYY-MM-DD days n [regex]
import sys, polars as pl, datetime as dt
F = "/Users/phosphorus/projects/prismql-data/ai-village/village_embeddings_2026-09-29/3_village_full_with_text.parquet"
agent, day, days, n = sys.argv[1], dt.date.fromisoformat(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
rx = sys.argv[5] if len(sys.argv) > 5 else None
t = (pl.scan_parquet(F).filter((pl.col("kind") == "THOUGHT") & (pl.col("agent") == agent))
     .select("time", "of", "text").collect().with_columns(pl.col("time").dt.date().alias("day"))
     .filter(pl.col("day").is_between(day - dt.timedelta(days=days), day + dt.timedelta(days=days)))
     .unique("text", keep="first").sort("time"))
if rx:
    print(t.group_by(pl.col("day") >= day).agg(pl.len(), pl.col("text").str.contains(rx).mean()))
    t = t.filter(pl.col("text").str.contains(rx))
for lab, sub in [("BEFORE", t.filter(pl.col("day") < day)), ("AFTER", t.filter(pl.col("day") >= day))]:
    print(f"--- {lab} ({sub.height})")
    for r in sub.sample(min(n, sub.height), seed=2).sort("time").iter_rows(named=True):
        txt = r["text"]
        if rx:
            import re
            m = re.search(rx, txt); s = max(0, m.start() - 150) if m else 0
            txt = txt[s:s + 330]
        else:
            txt = txt[:330]
        print(f"[{str(r['time'])[:16]} {r['of']}] {txt!r}")
