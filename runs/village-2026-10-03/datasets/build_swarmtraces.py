"""SwarmTraces -> event table for structural analysis only.
Stream order: payload id order, each payload's children (responses / recovered text) placed right after it.
time: an epoch literal found in the row's own text (July 2026 only), else null -- sparse (~0.7%).
actor: self-chosen User-Agent label where one exists. Coarse fields only; no decoding."""
import polars as pl
B = "/Users/phosphorus/projects/prismql-data/swarmtraces/"
df = pl.read_parquet(B + "st_base.parquet")
ep = pl.read_parquet(B + "st_epochs.parquet").select("id", pl.col("ts").alias("time"))
df = df.join(ep, on="id", how="left")
# order key: children sit after their parent payload
par = df.select(pl.col("id").alias("parent_id"), pl.col("n").alias("pn"))
df = df.join(par, on="parent_id", how="left").with_columns(
    pl.coalesce("pn", "n").alias("anchor"), (pl.col("pn").is_not_null()).cast(pl.Int8).alias("is_child"))
t = pl.col("text")
ua = t.str.extract(r"(?i)user-agent['\"]?\s*[:,]\s*['\"]?([A-Za-z][A-Za-z0-9_\-\.]{1,40})", 1)
generic = r"(?i)^(UA|x|a|w|python|curl.*|wget|Mozilla.*|Infra.*|dav|huggingface_hub|.*bot|python-requests.*)$"
def has(p): return t.str.contains(p)
df = df.with_columns(
    ua.alias("ua_raw"),
    pl.when(ua.is_not_null() & ~ua.str.contains(generic)).then(ua.str.to_lowercase()).otherwise(None).alias("actor"),
    pl.when(has(r"(?i)huggingface|\[HF REPO")).then(pl.lit("hf"))
      .when(has(r"(?i)docker|registry-1|/v2/")).then(pl.lit("registry"))
      .when(has(r"(?i)artifactory")).then(pl.lit("artifactory"))
      .when(has(r"(?i)slack")).then(pl.lit("slack"))
      .when(has(r"(?i)kube|k8s")).then(pl.lit("k8s"))
      .when(has(r"(?i)github")).then(pl.lit("github"))
      .when(has(r"(?i)webhook|\[WEBHOOK|paste")).then(pl.lit("dropbox"))
      .otherwise(pl.lit("other")).alias("target"),
    pl.when(has(r"\bdef |import |subprocess|print\(")).then(pl.lit("py"))
      .when(has(r"fetch\(|document\.|XMLHttpRequest|=>|var |let ")).then(pl.lit("js"))
      .when(has(r"(?m)^\s*(curl|wget|echo|cat|ls) ")).then(pl.lit("sh"))
      .otherwise(pl.lit("other")).alias("lang"),
    t.str.extract_all(r"\[USER \d+\]").list.unique().list.join("|").alias("users"),
    t.str.extract_all(r"\[HF REPO \d+\]").list.unique().list.join("|").alias("repos"),
    t.str.extract_all(r"\[(?:SERVICE|PROXY|WEBHOOK) \d+").list.unique().list.join("|").alias("services"),
    t.str.count_matches(r"\[[A-Z][A-Z0-9 _:\-]*?\d+\]").alias("n_placeholders"),
    t.str.len_chars().alias("chars"),
)
df = df.sort("anchor", "is_child", "n").select(
    "id", "time", "kind", "actor", "ua_raw", "target", "lang", "users", "repos", "services",
    "n_placeholders", "chars", "parent_id", "anchor", "is_child", "tags", "n", "text")
df.write_parquet(B + "swarmtraces_raw.parquet")
print(df.height, df["time"].is_not_null().sum(), df["actor"].is_not_null().sum())
print(df.group_by("target").len().sort("len", descending=True))
print(df.group_by("lang").len().sort("len", descending=True))
