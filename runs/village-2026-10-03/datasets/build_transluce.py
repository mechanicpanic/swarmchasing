"""Transluce urlquery catalog -> event table. actor = data source (task proxy); kind = broad_class."""
import polars as pl
D = "/Users/phosphorus/projects/prismql-data/transluce-urlquery/urlquery-agent-activity-2026-09-22-v5/"
r = pl.read_csv(D + "all-reports.csv")
s = pl.read_csv(D + "report-sources.csv").select("report_id", "data_source", "source_basis", "matched_sources")
df = (r.join(s, on="report_id", how="left")
       .with_columns(pl.col("data_source").fill_null("(none)"))
       .select(pl.col("report_id").alias("id"), pl.col("report_date_utc").alias("time"),
               pl.col("broad_class").alias("kind"), pl.col("data_source").alias("actor"),
               "confidence", "disposition", "source_basis", "matched_sources",
               pl.col("why_included").alias("text")))
df.write_parquet("/Users/phosphorus/projects/prismql-data/transluce-urlquery/urlquery_raw.parquet")
print(df.height)
