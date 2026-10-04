# Separate village-wide shifts from agent-specific ones.
# A flag is "village" if, for the same feature and direction, >= 3 agents AND
# >= 25% of agents with data that week flag within +-1 week. Writes
# changepoints.parquet (all flags, with a scope column and cluster size) and
# village_clusters.parquet.
import polars as pl

OUT = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/leads-changepoints/"
cp = pl.read_parquet(OUT + "changepoints_raw.parquet")
w = pl.read_parquet(OUT + "weekly.parquet").filter(pl.col("n") >= 10)
# agents with data around each week, per feature
elig = w.select("agent", "feature", "week").unique()

rows = []
for r in cp.iter_rows(named=True):
    lo, hi = r["week"] - pl.duration(weeks=1), r["week"] + pl.duration(weeks=1)
    same = cp.filter((pl.col("feature") == r["feature"]) & (pl.col("direction") == r["direction"])
                     & (pl.col("week") >= r["week"] - __import__("datetime").timedelta(weeks=1))
                     & (pl.col("week") <= r["week"] + __import__("datetime").timedelta(weeks=1)))
    n_ag = same["agent"].n_unique()
    n_el = elig.filter((pl.col("feature") == r["feature"]) & (pl.col("week") == r["week"]))["agent"].n_unique()
    rows.append(dict(cluster_agents=n_ag, eligible_agents=n_el, cluster_members=", ".join(sorted(same["agent"].unique()))))
cp = pl.concat([cp, pl.DataFrame(rows)], how="horizontal").with_columns(
    (pl.col("cluster_agents") / pl.col("eligible_agents").clip(1, None)).alias("cluster_frac"))
cp = cp.with_columns(
    pl.when((pl.col("cluster_agents") >= 3) & (pl.col("cluster_frac") >= 0.25)).then(pl.lit("village"))
    .when(pl.col("cluster_agents") >= 2).then(pl.lit("shared"))
    .otherwise(pl.lit("agent")).alias("scope"),
    (pl.col("after") - pl.col("before")).alias("delta"),
    pl.when(pl.col("before").abs() > 1e-9).then(pl.col("after") / pl.col("before")).alias("ratio"),
).sort("d", descending=True)
cp.write_parquet(OUT + "changepoints.parquet")
print(cp.group_by("scope").agg(pl.len(), pl.col("abrupt").sum()))

# ---- annotate with scaffolding CHANGELOG entries and goal changes near each flag ----
import re, json, gzip, datetime as dt
ROOT = "/Users/phosphorus/projects/prismql-data/ai-village/"
log, cur = [], None
for line in open(ROOT + "CHANGELOG.md"):
    m = re.match(r"## (\d{4}-\d{2}-\d{2})", line)
    if m: cur = dt.date.fromisoformat(m.group(1)); continue
    if cur and line.startswith("- **["):
        log.append((cur, re.sub(r"\s+", " ", line[2:].strip())[:160]))
goals = [(dt.date.fromisoformat(g["start_time"][:10]), g["goal"][:80]) for g in map(json.loads, gzip.open(ROOT + "village_goals.jsonl.gz"))]
names = {a["id"]: a["name"] for a in map(json.loads, gzip.open(ROOT + "agents.jsonl.gz"))}
agoals = [(names.get(g["agent_id"]), dt.date.fromisoformat((g["start_time"] or g["created_at"])[:10]), g["short_name"]) for g in map(json.loads, gzip.open(ROOT + "agent_goals.jsonl.gz"))]


def near(r):
    w0 = r["week"].date() - dt.timedelta(days=7); w1 = r["week"].date() + dt.timedelta(days=7)
    cl = [f"{d}: {t}" for d, t in log if w0 <= d <= w1]
    gl = [f"{d}: {t}" for d, t in goals if w0 <= d <= w1]
    al = [f"{d}: {t}" for a, d, t in agoals if a == r["agent"] and w0 <= d <= w1]
    return dict(changelog_nearby=" | ".join(cl), village_goal_nearby=" | ".join(gl), agent_goal_nearby=" | ".join(al))


cp = pl.concat([cp, pl.DataFrame([near(r) for r in cp.iter_rows(named=True)])], how="horizontal")
cp = cp.filter(~pl.col("agent").is_in(["GPT-5.6 Terra", "GPT-5.6 Luna"])).with_columns(pl.col("cluster_members").str.replace_all("GPT-5.6 Terra|GPT-5.6 Luna", "(opted-out agent)"))
cp.write_parquet(OUT + "changepoints.parquet")
print(cp.select((pl.col("changelog_nearby") != "").mean()))
