# Candidate village coinages: Title-Case 2-3 word names first used by an agent,
# adopted by >=4 agents, with GRADUAL spread (not all same-day = broadcast).
import polars as pl
pl.Config.set_tbl_rows(400); pl.Config.set_tbl_width_chars(250); pl.Config.set_fmt_str_lengths(40)
chat = pl.read_parquet("../../chat_raw.parquet", columns=["id","time","kind","agent","text"])
tok = (chat.with_columns(pl.col("text").str.replace_all(r"https?://\S+", " ")
          .str.extract_all(r"\b[A-Z][a-z]+(?:[ \-][A-Z][a-z]+){1,2}\b").alias("g"))
       .explode("g").drop_nulls("g").unique(["id","g"]))
ag = tok.filter(pl.col("kind")=="agent")
hum = tok.filter(pl.col("kind")=="user").group_by("g").agg(pl.col("time").min().alias("human_first"))
firsts = ag.group_by("g","agent").agg(pl.col("time").min().alias("t")).sort("t")
s = (firsts.group_by("g").agg(pl.col("t").first().alias("first"), pl.col("agent").first().alias("origin"),
        pl.len().alias("n_agents"), pl.col("t").sort().alias("ts"))
     .filter(pl.col("n_agents")>=4)
     .with_columns(((pl.col("ts").list.get(1)-pl.col("first")).dt.total_hours()/24).alias("d2"),
                   ((pl.col("ts").list.get(3)-pl.col("first")).dt.total_hours()/24).alias("d4"),
                   ((pl.col("ts").list.last()-pl.col("first")).dt.total_hours()/24).alias("dlast"))
     .join(hum, on="g", how="left")
     .filter(pl.col("human_first").is_null() | (pl.col("human_first")>pl.col("first")))
     .join(ag.group_by("g").agg(pl.len().alias("uses")), on="g"))
s.drop("ts").write_parquet("coinage_candidates_raw.parquet")
print(s.filter((pl.col("d4")>=2)&(pl.col("uses")>=15)).drop("ts").sort("n_agents",descending=True).head(300))
