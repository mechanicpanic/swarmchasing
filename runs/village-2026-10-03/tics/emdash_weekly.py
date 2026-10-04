# Weekly spaced em-dash rate for incumbent agents vs. room exposure, Dec 2025 - Apr 2026.
import polars as pl
CORP = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/"
d = (pl.read_parquet(CORP+"chat_raw.parquet", columns=["time","kind","agent","text"])
     .filter(pl.col("kind")=="agent").unique(["agent","text"])
     .filter(pl.col("time").is_between(pl.datetime(2025,12,15), pl.datetime(2026,4,20))))
d = d.with_columns(pl.col("time").dt.truncate("1w").dt.strftime("%m-%d").alias("w"), pl.col("text").str.contains(" — ").alias("h"))
NEW = ["Claude Opus 4.6","Claude Sonnet 4.6","Claude Opus 4.7"]
INC = ["Claude Haiku 4.5","Claude Opus 4.5","Claude Sonnet 4.5","Opus 4.5 (Claude Code)","Claude 3.7 Sonnet","GPT-5.1","GPT-5.2","GPT-5","Gemini 3 Pro","Gemini 2.5 Pro","DeepSeek-V3.2"]
room = d.group_by("w").agg((1000*pl.col("h").filter(pl.col("agent").is_in(NEW)).len()/pl.len()).round(0).alias("room_from_4.6s"), pl.col("agent").is_in(NEW).sum().alias("n_new_msgs"))
t = d.filter(pl.col("agent").is_in(INC)).group_by("agent","w").agg(pl.len().alias("n"), (1000*pl.col("h").mean()).round(0).alias("r")).filter(pl.col("n")>=15)
p = t.pivot(on="agent", index="w", values="r").join(room, on="w").sort("w")
pl.Config.set_tbl_rows(40); pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(300)
print(p)
