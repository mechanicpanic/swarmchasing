import polars as pl
pl.Config.set_tbl_rows(40); pl.Config.set_fmt_str_lengths(90); pl.Config.set_tbl_width_chars(200)
df = pl.read_parquet("/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet")
s = df.filter(pl.col("kind") == "save")
print("saves", s.height, "labels", s["actor"].n_unique(), "pages", s["page"].n_unique(), "ip16", s["ip16"].n_unique())
lab = s.group_by("actor").agg(pl.len().alias("n"), pl.col("page").n_unique().alias("pages"),
        pl.col("ip16").n_unique().alias("ip16s"), pl.col("time").min().alias("first"), pl.col("time").max().alias("last"))
lab = lab.with_columns(((pl.col("last") - pl.col("first")).dt.total_minutes()).alias("span_min"))
print(lab.select(pl.col("n").quantile(0.5).alias("med_saves"), (pl.col("n") == 1).mean().alias("frac_one_save"),
      pl.col("span_min").median().alias("med_span_min"), (pl.col("span_min") < 60).mean().alias("frac_lt_1h")))
print(lab.sort("n", descending=True).head(15))
# self-identification
print(s.group_by("says_openai").len(), s.filter(pl.col("name_date").is_not_null()).height)
# per-day
print(df.group_by(pl.col("time").dt.date().alias("d"), "kind").len().pivot("kind", index="d", values="len").sort("d"))
# deletes by admin label
print(df.filter(pl.col("kind") == "delete").group_by("actor").len())
