"""C34 shared loading: agent saves, deletion runs, other-venue rows (wiki_msgs + swarm_msgs, env REPO, default '.').
Save = one revision (distinct `rev`) of kind add/remove by a non-admin label; dropped: revs carrying the Loop broadcast
(text_key 146d7f0c0cfc7856) and revs whose added text starts with #REDIRECT/#WEITERLEITUNG. Deletion run = admin
deletes with no gap over 10 minutes (the 10-400 subset is the server's RUN(field(kind, delete)){10,400} DURING
10 minutes). Agent writing stops 2026-06-22 09:20:04, so only runs before that can show a response."""
import os
from datetime import datetime, timedelta, timezone

import polars as pl

REPO = os.environ.get("REPO", ".")
BROADCAST, HUB = "146d7f0c0cfc7856", "dse~WillkommenImWiki"
REDIR = r"(?i)^\s*#(redirect|weiterleitung)"
STOP = datetime(2026, 6, 22, 9, 20, 5, tzinfo=timezone.utc)
DAY = timedelta(hours=24)
OTHER = ("probier", "fractal", "dorfwiki")  # other wikis in the export; dse is the swept one


def saves(no_hub=False):
    w = pl.read_parquet(f"{REPO}/data/wiki_msgs.parquet")
    s = (w.filter(pl.col("kind").is_in(["add", "remove"]) & ~pl.col("label").str.starts_with("[Admin"))
         .group_by("rev").agg(pl.col("page", "wiki", "page_family", "label", "time", "rev_seq").first(),
                              (pl.col("text_key") == BROADCAST).any().alias("bc"),
                              (pl.col("kind").eq("add") & pl.col("text").str.contains(REDIR)).any().alias("redir"),
                              pl.col("text_key").filter(pl.col("kind") == "add").alias("keys"))
         .filter(~pl.col("bc") & ~pl.col("redir")).drop("bc", "redir").sort("time"))
    if no_hub: s = s.filter(pl.col("page") != HUB)
    return s


def deletions():
    w = pl.read_parquet(f"{REPO}/data/wiki_msgs.parquet")
    d = w.filter(pl.col("kind") == "delete").select("id", "time", "page", "page_family").sort("time")
    return d.with_columns((pl.col("time").diff().dt.total_seconds().fill_null(1e9) > 600).cum_sum().alias("run"))


def runs(d, min_size=1):
    """Deletion runs whose 24 h after-window closes before the stop: (run, start, end, pages, families)."""
    r = (d.group_by("run").agg(pl.col("time").min().alias("start"), pl.col("time").max().alias("end"),
                               pl.col("page"), pl.col("page_family").drop_nulls().unique().alias("fams"), pl.len().alias("n"))
         .filter((pl.col("start") > datetime(2026, 6, 10, tzinfo=timezone.utc)) & (pl.col("start") + DAY <= STOP)
                 & (pl.col("n") >= min_size)).sort("start"))
    return r


def explorer():
    """Explorer rows from other venues with a time. 'report authors' rows are dated by write date (verified);
    community-found rows are kept apart and never quoted as agent text."""
    s = pl.read_parquet(f"{REPO}/data/swarm_msgs.parquet").filter((pl.col("source") == "explorer") & pl.col("time").is_not_null())
    return (s.filter(pl.col("found_by") == "report authors").select("time", "wiki"),
            s.filter(pl.col("found_by").str.starts_with("community")).select("time", "wiki"))


def count_in(times, lo, hi):
    """Number of sorted datetimes in [lo, hi)."""
    import bisect
    return bisect.bisect_left(times, hi) - bisect.bisect_left(times, lo)
