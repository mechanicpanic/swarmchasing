"""wiki_msgs (dse/probier/fractal/dorfwiki, with labels) + the explorer's timed rows from other venues (pastebins,
other wikis; no labels) → one stream across venues. `wiki` names the venue; `source` = wiki | explorer.
Output: data/swarm_msgs_rows.parquet (then `prismql ingest table … --id id --time time --sort seq`)."""

import polars as pl

w = pl.read_parquet("data/wiki_msgs_rows.parquet").with_columns(
    pl.lit("wiki").alias("source")
)
e = (
    pl.read_parquet("data/explorer_sites_rows.parquet")
    .filter(pl.col("time").is_not_null())
    .drop("shared_urls")
    .rename({"site": "wiki"})
    .with_columns(pl.lit("explorer").alias("source"))
)
df = (
    pl.concat([w, e], how="diagonal_relaxed")
    .sort("time", "source", "seq")
    .drop("seq")
    .with_row_index("seq")
)
assert df["id"].is_unique().all()
df.write_parquet("data/swarm_msgs_rows.parquet")
print(df.height, "rows |", df.group_by("source").len().to_dicts())
shared = (
    df.filter(pl.col("text_key").is_not_null())
    .group_by("text_key")
    .agg(pl.col("source").n_unique().alias("n"))
    .filter(pl.col("n") > 1)
)
print("texts seen both in the wiki export and on other venues:", shared.height)
