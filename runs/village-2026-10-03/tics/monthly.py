# Monthly rate (per 1k msgs) of a regex per agent: tests generation vs. in-room drift.
import sys, polars as pl
rx = sys.argv[1]; src = sys.argv[2] if len(sys.argv) > 2 else "chat"
agents = sys.argv[3].split("|") if len(sys.argv) > 3 else None
CORP = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/"
if src == "chat":
    d = pl.read_parquet(CORP+"chat_raw.parquet", columns=["time","kind","agent","text"]).filter(pl.col("kind")=="agent")
else:
    d = (pl.scan_parquet(CORP+"../village_embeddings_2026-09-29/3_village_full_with_text.parquet")
         .filter(pl.col("kind")=="THOUGHT").select("time","agent","text").collect().with_columns(pl.col("time").dt.replace_time_zone(None)))
d = d.unique(["agent","text"]).filter(~pl.col("agent").is_in(["GPT-5.6 Terra","GPT-5.6 Luna"]))
if agents: d = d.filter(pl.col("agent").is_in(agents))
d = d.with_columns(pl.col("time").dt.strftime("%y-%m").alias("m"), pl.col("text").str.contains(rx).alias("h"))
t = d.group_by("agent","m").agg(pl.len().alias("n"), (1000*pl.col("h").mean()).round(0).alias("r")).filter(pl.col("n")>=30)
p = t.pivot(on="m", index="agent", values="r", sort_columns=True)
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(300); pl.Config.set_fmt_str_lengths(22)
print(p.sort(p.columns[1:], nulls_last=True))
