# Candidate memes: 3-word phrases that appear late (not generic English from
# day one), spread to many distinct agents, and have one clear first user.
import polars as pl
pl.Config.set_tbl_rows(40); pl.Config.set_fmt_str_lengths(60)
chat = pl.read_parquet("chat_raw.parquet", columns=["id","time","kind","agent","text"])
words = (chat.with_columns(pl.col("text").str.to_lowercase()
                          .str.replace_all(r"https?://\S+", " ")
                          .str.extract_all(r"[a-z][a-z'\-]+").alias("w"))
             .filter(pl.col("w").list.len() >= 3))
tri = (words.with_columns(pl.concat_list([pl.col("w").list.slice(0, pl.col("w").list.len()-2),]).alias("a"))
       .select("id","time","kind","agent","w")
       .with_columns(pl.int_ranges(0, pl.col("w").list.len()-2).alias("i"))
       .explode("i")
       .with_columns(pl.concat_str([pl.col("w").list.get(pl.col("i")), pl.col("w").list.get(pl.col("i")+1), pl.col("w").list.get(pl.col("i")+2)], separator=" ").alias("g"))
       .select("id","time","kind","agent","g").unique(["id","g"]))
agents = tri.filter(pl.col("kind")=="agent")
first = agents.sort("time").group_by("g").agg(
    pl.col("time").first().alias("first"), pl.col("agent").first().alias("origin"),
    pl.col("agent").n_unique().alias("n_agents"), pl.len().alias("uses"),
    pl.col("agent").unique(maintain_order=True).head(5).alias("first_adopters"),
    pl.col("time").filter(pl.col("agent") != pl.col("agent").first()).first().alias("second_agent_at"))
human = tri.filter(pl.col("kind")=="user").group_by("g").agg(pl.col("time").min().alias("human_first"))
c = (first.join(human, on="g", how="left")
     .filter((pl.col("n_agents") >= 8) & (pl.col("uses") >= 40)
             & (pl.col("first") > pl.datetime(2025, 6, 1)))
     .with_columns(((pl.col("human_first").is_null()) | (pl.col("human_first") > pl.col("first"))).alias("agent_born"))
     .sort("n_agents", descending=True))
c.write_parquet("analysis/meme_candidates.parquet")
print(c.height, "candidates")
print(c.filter("agent_born").select("g","origin","first","n_agents","uses").head(40))
