"""Which link hosts spread between labels, and how fast (first use per label)."""
import polars as pl
pl.Config.set_tbl_rows(40); pl.Config.set_fmt_str_lengths(60); pl.Config.set_tbl_width_chars(200)
df = pl.read_parquet("/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet").filter(pl.col("kind") == "save")
h = df.select("time", "actor", "ip16", "page", pl.col("text").str.extract_all(r"https?://([A-Za-z0-9\.\-]+)").alias("u")).explode("u").drop_nulls()
h = h.with_columns(pl.col("u").str.replace(r"^https?://", "").str.to_lowercase().str.replace(r"^www\.", "").alias("host")).unique(["time", "actor", "page", "host"])
h = h.filter(~pl.col("host").str.contains(r"wikiservice\.at|prowiki\.org"))
first = h.sort("time").group_by("host", "actor").agg(pl.col("time").first()).sort("time")
agg = first.group_by("host").agg(pl.len().alias("labels"), pl.col("time").min().alias("first"),
        pl.col("time").sort().get(pl.min_horizontal(pl.len() - 1, 9)).alias("t10th"))
agg = agg.with_columns(((pl.col("t10th") - pl.col("first")).dt.total_hours()).alias("h_to_10_labels"))
print(agg.sort("labels", descending=True).head(35))
agg.write_parquet("/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/datasets/collusion_host_spread.parquet")
