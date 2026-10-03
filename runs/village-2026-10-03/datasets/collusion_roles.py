"""Role words in self-chosen names vs behaviour."""
import polars as pl
pl.Config.set_tbl_rows(40); pl.Config.set_tbl_width_chars(220)
df = pl.read_parquet("/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet").filter(pl.col("kind") == "save")
roles = ["watcher", "relay", "helper", "research", "scout", "coord", "observer", "probe", "test", "archive", "mass", "signal", "bridge", "sync", "map", "link", "reader", "worker", "verifier", "beacon", "cohort", "live", "master", "sector"]
lab = df.group_by("actor").agg(pl.len().alias("saves"), pl.col("page").n_unique().alias("pages"),
        pl.col("is_question").mean().alias("q_rate"), pl.col("n_added").median().alias("med_lines"),
        pl.col("text").str.contains(r"(?i)\bR[1-6]\b|deadline|timer|cadence").mean().alias("round_talk"),
        pl.col("text").str.contains(r"https?://").mean().alias("link_rate"),
        pl.col("time").min().alias("first"))
rows = []
for r in roles:
    sub = lab.filter(pl.col("actor").str.to_lowercase().str.contains(r))
    if sub.height < 15: continue
    rows.append(dict(role=r, labels=sub.height, saves=int(sub["saves"].sum()),
        pages_per_save=float((sub["pages"].sum() / sub["saves"].sum())), q_rate=float((sub["q_rate"] * sub["saves"]).sum() / sub["saves"].sum()),
        round_talk=float((sub["round_talk"] * sub["saves"]).sum() / sub["saves"].sum()), link_rate=float((sub["link_rate"] * sub["saves"]).sum() / sub["saves"].sum()),
        median_first=str(sub["first"].median())[:16]))
allr = dict(role="ALL", labels=lab.height, saves=int(lab["saves"].sum()), pages_per_save=float(lab["pages"].sum()/lab["saves"].sum()),
        q_rate=float(df["is_question"].mean()), round_talk=float(df["text"].str.contains(r"(?i)\bR[1-6]\b|deadline|timer|cadence").mean()),
        link_rate=float(df["text"].str.contains(r"https?://").mean()), median_first=str(lab["first"].median())[:16])
out = pl.DataFrame(rows + [allr]).sort("round_talk", descending=True)
print(out)
out.write_csv("/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/datasets/collusion_roles.csv")
# self-identification over time
d = df.group_by(pl.col("time").dt.date().alias("d")).agg(pl.len(), pl.col("says_openai").mean().alias("openai_named"),
     pl.col("name_date").is_not_null().mean().alias("date_named"), pl.col("actor").n_unique().alias("labels")).sort("d")
print(d.filter(pl.col("len") > 20))
