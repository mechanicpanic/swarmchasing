"""urlquery reports (Transluce) + collusion.wiki messages → one stream for cross-trace lead-lag.
Both halves share `id` (prefixed), `time` (UTC), `source` (urlquery | wiki) and `family` (a common topic key).
urlquery: family from data_source. wiki: one row per distinct message (records.jsonl) at its FIRST appearance
(revision bodies repeat old text, so revisions would overcount); family from the page family, else from keywords in the text.
Output: data/uq_wiki_union.parquet (then `prismql ingest table … --id id --time time --sort time`)."""

import ast
import datetime as _dt
import gzip
import json
import re

import polars as pl

W = "/Users/aleph/Projects/research/prismql-research/hackathon/swarmchasing/data/"
SRC2FAM = {
    "SEC county data": "sec-county",
    "AIHW": "aihw",
    "IHME": "ihme",
    "DataUSA": "datausa",
    "MAX budget documents": "max-budget",
    "Maryland school report cards": "maryland-schools",
    "UNM digital library": "unm-library",
    "UNCTAD": "unctad",
    "Thrill Data": "thrill-data",
}
KW = [
    ("sec-county", r"sec\.gov/files/county|county\.json"),
    ("max-budget", r"max\.gov"),
    ("maryland-schools", r"maryland"),
    ("unm-library", r"unm\.edu|digitalrepository\.unm"),
    ("aihw", r"aihw"),
    ("ihme", r"ihme|healthdata\.org"),
    ("datausa", r"datausa"),
    ("unctad", r"unctad"),
    ("thrill-data", r"thrill"),
]


def fam_from_page(pf):
    if not pf:
        return None
    for p, f in (("aihw", "aihw"), ("ihme", "ihme"), ("datausa", "datausa")):
        if pf.startswith(p):
            return f
    return None


u = pl.read_parquet("data/transluce/urlquery.parquet").filter(
    pl.col("disposition") == "included"
)
uq = u.select(
    ("uq:" + pl.col("id")).alias("id"),
    "time",
    pl.lit("urlquery").alias("source"),
    pl.col("data_source").replace_strict(SRC2FAM, default=None).alias("family"),
    pl.col("data_source"),
    "broad_class",
    "confidence",
    pl.lit(None, dtype=pl.Utf8).alias("page"),
    pl.lit(None, dtype=pl.Utf8).alias("page_family"),
    "text",
)
with gzip.open(W + "pages.jsonl.gz", "rt") as fh:
    pages = [json.loads(line) for line in fh]
pfam = {p["page_key"]: p.get("page_family") for p in pages}


def _iso(v):
    # ISO strings as they are; unix seconds converted; 'current' and other markers are no time at all
    if not v:
        return None
    v = str(v)
    if v.isdigit():
        # only plausible unix seconds (2025-2026); other integers in this field are not times
        return (
            _dt.datetime.fromtimestamp(int(v), _dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            if 1735689600 <= int(v) < 1798761600
            else None
        )
    return v if re.match(r"\d{4}-\d{2}-\d{2}T", v) else None


rows = []
skipped = 0
with gzip.open(W + "records.jsonl.gz", "rt") as fh:
    record_lines = fh.readlines()
for line in record_lines:
    r = json.loads(line)
    o = (
        r["origins"]
        if isinstance(r["origins"], list)
        else ast.literal_eval(r["origins"])
    )
    o = [dict(x, _t=_iso(x.get("source_date_literal"))) for x in o]
    o = [x for x in o if x["_t"]]
    if not o:
        skipped += 1
        continue
    first = min(o, key=lambda x: x["_t"])
    page = first["source_id"].replace("/", "~", 1)
    pf = pfam.get(page)
    fam = fam_from_page(pf)
    if fam is None:
        t = (r["text"] or "").lower()
        fam = next((f for f, rx in KW if re.search(rx, t)), None)
    rows.append(
        {
            "id": "wk:" + r["id"][:24],
            "time": first["_t"],
            "source": "wiki",
            "family": fam,
            "data_source": None,
            "broad_class": None,
            "confidence": None,
            "page": page,
            "page_family": pf,
            "text": (r["text"] or "")[:4000],
        }
    )
wk = pl.DataFrame(rows).with_columns(
    pl.col("time")
    .str.to_datetime(time_zone="UTC")
    .dt.cast_time_unit(u["time"].dtype.time_unit)
)
out = pl.concat([uq, wk.select(uq.columns)], how="vertical_relaxed").sort("time")
out.write_parquet("data/uq_wiki_union.parquet")
print("wiki records without a usable first time:", skipped)
print(
    out.height,
    "rows |",
    out.group_by("source", "family")
    .len()
    .filter(pl.col("family").is_not_null())
    .sort("source", "len", descending=[False, True])
    .to_dicts(),
)
