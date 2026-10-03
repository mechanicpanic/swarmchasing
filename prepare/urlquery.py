"""Transluce "urlquery agent activity" release (https://transluce.org/agent-activity; the zip is downloaded by hand) →
data/transluce/urlquery.csv: one row per urlquery.net report with its disposition, confidence, class, data source and
why Transluce included it (then `prismql ingest table … --id id --time time --sort time`).
usage: uv run python prepare/urlquery.py ZIP"""

import io
import sys
import zipfile

import polars as pl

with zipfile.ZipFile(sys.argv[1]) as z:

    def table(name):
        (member,) = [n for n in z.namelist() if n.endswith("/" + name)]
        return pl.read_csv(io.BytesIO(z.read(member)), infer_schema_length=0)

    reports, sources = table("all-reports.csv"), table("report-sources.csv")

df = (
    reports.join(sources.select("report_id", "data_source"), on="report_id", how="left")
    .rename({"report_id": "id", "report_date_utc": "time", "why_included": "text"})
    .select(
        "id", "time", "disposition", "confidence", "broad_class", "data_source", "text"
    )
)
df.write_csv("data/transluce/urlquery.csv")
print(
    df.height,
    "reports,",
    df.filter(pl.col("disposition") == "included").height,
    "included",
)
