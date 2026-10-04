"""Label co-use of shared pseudonymous infrastructure; what kind of literal gave the dated rows their time. Prints counts only."""
import polars as pl, itertools, collections
df = pl.read_parquet("/Users/phosphorus/projects/prismql-data/swarmtraces/swarmtraces_raw.parquet")
d = df.filter(pl.col("time").is_not_null())
ctx = d.select(pl.col("text").str.contains(r"(?i)expires|signature|x-amz").alias("signed"),
               pl.col("text").str.contains(r"Date\.now|time\.time|ts=|t=").alias("clock"))
print("dated rows", d.height, "with signed-URL context", ctx["signed"].sum(), "with clock-ish params", ctx["clock"].sum())
print(d.group_by(pl.col("time").dt.date().alias("d")).len().sort("d"))
lab = df.filter(pl.col("actor").is_not_null())
infra = lab.select("actor", pl.concat_str([pl.col("repos"), pl.col("users")], separator="|").str.split("|").alias("x")).explode("x").filter(pl.col("x") != "")
g = infra.group_by("x").agg(pl.col("actor").unique())
pairs = collections.Counter()
for labs in g["actor"]:
    for a, b in itertools.combinations(sorted(labs), 2): pairs[(a, b)] += 1
nodes = set(a for p in pairs for a in p)
print("self-labels", lab["actor"].n_unique(), "with any shared repo/user", infra["actor"].n_unique(), "linked to another label via shared infra", len(nodes), "label pairs", len(pairs))
# connected components
par = {n: n for n in nodes}
def f(x):
    while par[x] != x: par[x] = par[par[x]]; x = par[x]
    return x
for a, b in pairs: par[f(a)] = f(b)
comp = collections.Counter(f(n) for n in nodes)
print("components sizes", sorted(comp.values(), reverse=True))
# id order vs time
for k in ["payload", "response", "recovered_text"]:
    s = d.filter(pl.col("kind") == k)
    print(k, s.height, "spearman(id, time)", round(s.select(pl.corr("n", pl.col("time").dt.epoch("s"), method="spearman")).item(), 3))
