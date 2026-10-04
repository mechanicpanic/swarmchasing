"""wiki saves + urlquery scans in one corpus, tagged with Transluce's own data-source markers (methods.json)."""
import json, polars as pl
T = "/Users/phosphorus/projects/prismql-data/transluce-urlquery/"
meth = json.load(open(T + "urlquery-agent-activity-2026-09-22-v5/methods.json"))
meth = meth if isinstance(meth, list) else meth.get("collections", meth.get("methods", []))
markers = [(m["label"], mk.lower()) for m in meth if isinstance(m, dict) and m.get("id", "").startswith("source:") for mk in m.get("markers", []) if len(mk) >= 6]
print(len(markers), markers[:8])
w = pl.read_parquet("/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet").filter(pl.col("kind") == "save")
low = pl.col("text").str.to_lowercase()
topic = pl.lit(None, dtype=pl.String)
for label, mk in reversed(markers):
    topic = pl.when(low.str.contains(mk, literal=True)).then(pl.lit(label)).otherwise(topic)
buckets = pl.read_parquet(T + "urlquery.parquet")["actor"].unique().to_list()
def norm(lbl):
    if lbl in buckets: return lbl
    first = lbl.split()[0].lower()
    c = [b for b in buckets if b.split()[0].lower() == first]
    return c[0] if len(c) == 1 else lbl
mp = {l: norm(l) for l, _ in markers}
print({k: v for k, v in mp.items() if k != v})
w = w.with_columns(topic.replace(mp).alias("topic")).select("id", "time", "kind", "actor", "page", "topic", "text")
u = pl.read_parquet(T + "urlquery.parquet").filter(pl.col("disposition") == "included").select(
    "id", "time", "kind", pl.lit("(urlquery)").alias("actor"), pl.lit("").alias("page"), pl.col("actor").alias("topic"), "text")
w.write_parquet(T + "u_wiki.parquet"); u.write_parquet(T + "u_urlquery.parquet")
print(w.group_by("topic").len().sort("len", descending=True).head(20))
