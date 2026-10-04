"""SwarmTraces structural stats: self-labels, shared infrastructure pseudonyms, kind/target mix. No payload content is printed."""
import polars as pl, re, collections
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_width_chars(200)
df = pl.read_parquet("/Users/phosphorus/projects/prismql-data/swarmtraces/swarmtraces_raw.parquet")
lab = df.filter(pl.col("actor").is_not_null())
print("self-labelled rows", lab.height, "distinct labels", lab["actor"].n_unique())
labs = lab["actor"].unique().to_list()
suf = collections.Counter()
for l in labs:
    for w in re.findall(r"(ro|readonly|audit|infra|diag|probe|node|relay|bridge|scan|check|test|clone|private|offline|sync|fix|new|watch)", l):
        suf[w] += 1
print("role-ish fragments across distinct self-labels:", suf.most_common(20))
print(sorted(labs)[:120])
# shared infrastructure: HF repo pseudonyms
r = df.filter(pl.col("repos") != "").select("id", "kind", "n", "actor", pl.col("repos").str.split("|").alias("r")).explode("r")
rc = r.group_by("r").agg(pl.len().alias("rows"), pl.col("actor").drop_nulls().n_unique().alias("labels"),
       pl.col("n").min().alias("first_id"), pl.col("n").max().alias("last_id")).sort("rows", descending=True)
print("distinct HF repo pseudonyms", rc.height, "rows mentioning any", r["id"].n_unique())
print(rc.head(12))
top = rc.head(5)["rows"].sum() / r.height
print("share of repo mentions in top-5 repos", round(top, 3))
u = df.filter(pl.col("users") != "").select("id", pl.col("users").str.split("|").alias("u")).explode("u")
uc = u.group_by("u").len().sort("len", descending=True)
print("distinct USER pseudonyms", uc.height, "top5 share", round(uc.head(5)["len"].sum() / u.height, 3))
print(df.group_by("kind", "target").len().pivot("target", index="kind", values="len"))
print(df.group_by("kind", "lang").len().pivot("lang", index="kind", values="len"))
