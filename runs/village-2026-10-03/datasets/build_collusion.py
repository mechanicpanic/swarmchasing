"""collusion.wiki -> one event table (saves w/ added text, deletes, reverts, probes)."""
import gzip, json, polars as pl
D = "/Users/phosphorus/projects/prismql-data/collusion-wiki/"
rows = []
for l in gzip.open(D + "revisions.jsonl.gz", "rt"):
    d = json.loads(l)
    lines = (d["body"] or "").split("\n")
    added = []
    for h in d["hunks"] or []:
        if h["op"] in ("insert", "replace"):
            added += lines[h["b0"]:h["b1"]]
    rows.append(dict(id="save:" + d["rev_id"], time=d["time"], kind="save", actor=d["label"] or "(unsigned)",
                     wiki=d["wiki"], page=d["name"], seq=d["seq"], ip16=d["ip16"],
                     summary=d["change_summary"] or "", body_len=d["body_len"],
                     n_added=len(added), text="\n".join(added)[:8000], time_grade=d["time_grade"]))
for l in gzip.open(D + "events.jsonl.gz", "rt"):
    d = json.loads(l)
    t = d["event_type"]
    if t == "save":
        continue
    rows.append(dict(id=d["event_id"], time=d["time"], kind=t, actor=d.get("actor_label") or ("(prober)" if t == "probe" else "(unknown)"),
                     wiki=d.get("wiki") or "dse", page=d.get("page") or "", seq=None, ip16=d.get("ip16") or "",
                     summary=d.get("change_summary") or d.get("param_family") or "", body_len=None, n_added=None,
                     text=(d.get("change_summary") or "") if t != "probe" else f"probe {d.get('request_action')} {d.get('param_family')}",
                     time_grade=d.get("time_grade")))
df = pl.DataFrame(rows, infer_schema_length=None)
# name features
df = df.with_columns(
    pl.col("actor").str.contains(r"(?i)openai|oai").alias("says_openai"),
    pl.col("actor").str.extract(r"(?i)(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*?(\d{1,2})", 0).alias("name_date"),
)
df.write_parquet(D + "collusion_raw.parquet")
print(df.group_by("kind").len(), df.height)
