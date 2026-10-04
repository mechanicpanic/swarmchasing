import polars as pl
pl.Config.set_tbl_rows(50); pl.Config.set_tbl_width_chars(220); pl.Config.set_fmt_str_lengths(40)
u = pl.read_parquet("/Users/phosphorus/projects/prismql-data/transluce-urlquery/urlquery.parquet").filter(pl.col("disposition") == "included")
f = u.group_by("actor", "kind").agg(pl.col("time").min()).pivot("kind", index="actor", values="time")
cnt = u.group_by("actor").agg(pl.len().alias("n"), pl.col("time").min().alias("first"), pl.col("time").max().alias("last"),
      (pl.col("confidence") == "significant").mean().round(2).alias("sig"))
f = f.join(cnt, on="actor").sort("n", descending=True)
f = f.with_columns(((pl.col("custom_program") - pl.col("source_request")).dt.total_hours()).alias("h_req_to_prog"))
print(f.select("actor", "n", "sig", "first", "last", "h_req_to_prog").head(25))
both = f.filter(pl.col("custom_program").is_not_null() & pl.col("source_request").is_not_null())
print("sources with both:", both.height, "request first:", (both["h_req_to_prog"] > 0).sum())
# daily: wiki saves vs urlquery scans, May 15 - Jul 15
w = pl.read_parquet("/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet").filter(pl.col("kind") == "save")
wd = w.group_by(pl.col("time").dt.date().alias("d")).agg(pl.len().alias("wiki_saves"))
ud = u.group_by(pl.col("time").dt.date().alias("d")).agg(pl.len().alias("urlquery"), (pl.col("kind") == "custom_program").sum().alias("uq_prog"))
j = ud.join(wd, on="d", how="full", coalesce=True).fill_null(0).sort("d").filter(pl.col("d").is_between(pl.date(2026, 5, 20), pl.date(2026, 7, 5)))
print(j)
print("spearman daily (May20-Jul5):", j.select(pl.corr("urlquery", "wiki_saves", method="spearman")).item())
