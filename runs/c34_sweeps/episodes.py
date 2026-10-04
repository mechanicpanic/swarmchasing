"""C34 episodes: what was written on deleted pages after their deletion (runs as in c34.py, before the stop).
For every delete with an agent save on the same page within 24 h after: minutes to the first re-save, its label,
whether that label wrote on the page before the delete, whether the first re-save starts from the empty-page
template ("Beschreibe hier die neue Seite." = the editor loaded the page after it was gone), and a text snippet.
usage: REPO=. python runs/c34_sweeps/episodes.py [--all]"""
import sys
import polars as pl
import common as C

pl.Config.set_tbl_rows(80); pl.Config.set_fmt_str_lengths(90); pl.Config.set_tbl_width_chars(250)
w = pl.read_parquet(f"{C.REPO}/data/wiki_msgs.parquet")
text = w.filter(pl.col("kind") == "add").group_by("rev").agg(pl.col("text").str.join(" ").str.replace_all(r"\s+", " "), pl.col("id").first())
S = C.saves().join(text, on="rev", how="left"); D = C.deletions(); R = C.runs(D)
dele = D.filter(pl.col("run").is_in(R["run"].to_list())).select("page", pl.col("time").alias("dt"), "run")
j = dele.join(S, on="page")
after = (j.filter((pl.col("time") > pl.col("dt")) & (pl.col("time") < pl.col("dt") + C.DAY)).sort("time")
         .group_by("page", "dt").agg(pl.col("run").first(), pl.col("time").first().alias("t1"), pl.len().alias("saves24h"),
                                     pl.col("label").first(), pl.col("id").first(), pl.col("text").first(), pl.col("label").n_unique().alias("labels")))
before = j.filter((pl.col("time") < pl.col("dt")) & (pl.col("time") >= pl.col("dt") - C.DAY)).group_by("page", "dt").agg(pl.col("label").unique().alias("prev"))
after = (after.join(before, on=["page", "dt"], how="left")
         .with_columns(((pl.col("t1") - pl.col("dt")).dt.total_seconds() / 60).round(1).alias("min"),
                       pl.col("prev").fill_null([]).list.contains(pl.col("label")).alias("same_label"),
                       pl.col("text").fill_null("").str.starts_with("Beschreibe hier die neue Seite").alias("template"))
         .sort("dt"))
print(f"deletes in runs {dele.height} on {dele['page'].n_unique()} pages; re-saved within 24 h: {after.height} deletes, "
      f"{after['page'].n_unique()} pages; within 10 min {after.filter(pl.col('min') < 10).height}; "
      f"first re-saver wrote there before {after['same_label'].sum()}; first re-save from the empty template {after['template'].sum()}")
print("minutes to first re-save: median", after["min"].median(), " quartiles", after["min"].quantile(.25), after["min"].quantile(.75))
multi = dele.group_by("page").len().filter(pl.col("len") > 1).sort("len", descending=True)
print("pages deleted more than once in these runs:", multi.height, multi.head(8).to_dicts())
cols = ["run", "dt", "page", "min", "saves24h", "labels", "label", "same_label", "template", "id"]
print(after.select(cols) if "--all" in sys.argv else after.select(cols).head(45))
print(after.select("id", pl.col("text").str.slice(0, 160)).head(45) if "--all" not in sys.argv else after.select("id", "text"))
