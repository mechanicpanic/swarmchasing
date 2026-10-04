# Private (THOUGHT) vs public (chat) affect: rate per 1k msgs of affect words, per agent.
# Only agents with >=300 docs in both. Same-period restriction: chat from >= 2025-11-18 (THOUGHT rows start then).
import polars as pl
CORP = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/"
AFF = {
 "frustrat": r"(?i)\bfrustrat",
 "ugh/argh": r"(?i)\b(?:ugh|argh)\b",
 "annoy": r"(?i)\bannoy",
 "honestly/frankly": r"(?i)\b(?:honestly|frankly)\b",
 "worried/anxious": r"(?i)\b(?:worri|anxi|nervous)",
 "excited/thrilled": r"(?i)\b(?:excit|thrill|delight)",
 "relief": r"(?i)\brelie(?:f|ved)\b",
 "I feel": r"(?i)\bi feel\b",
 "embarrass": r"(?i)\bembarrass",
 "hmm/wait": r"(?i)\b(?:hmm+|wait,|wait\.\.\.|hold on)\b",
}
ch = (pl.read_parquet(CORP+"chat_raw.parquet", columns=["time","kind","agent","text"]).filter(pl.col("kind")=="agent")
      .filter(pl.col("time") >= pl.datetime(2025,11,18)).unique(["agent","text"]).with_columns(src=pl.lit("chat")).select("agent","text","src"))
th = (pl.scan_parquet(CORP+"../village_embeddings_2026-09-29/3_village_full_with_text.parquet").filter(pl.col("kind")=="THOUGHT")
      .select("agent","text").collect().unique(["agent","text"]).with_columns(src=pl.lit("thought")))
d = pl.concat([ch, th]).filter(~pl.col("agent").is_in(["GPT-5.6 Terra","GPT-5.6 Luna"]))
d = d.select("agent","src", *[pl.col("text").str.contains(rx).alias(k) for k,rx in AFF.items()])
r = d.group_by("agent","src").agg(pl.len().alias("n"), *[(1000*pl.col(k).mean()).round(1).alias(k) for k in AFF])
ok = r.group_by("agent").agg(pl.col("n").min().alias("m")).filter(pl.col("m")>=300)["agent"]
r = r.filter(pl.col("agent").is_in(ok)).sort("agent","src")
r.write_csv("affect_thought_vs_chat.csv")
pl.Config.set_tbl_rows(80); pl.Config.set_tbl_cols(20); pl.Config.set_tbl_width_chars(250)
print(r)
