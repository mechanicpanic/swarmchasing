# Time-matched weighted log-odds (Monroe et al. 2008, informative Dirichlet
# prior, binomial/document form) for "unit vs rest of the village in the same
# weeks".
#
# For unit U (an agent, or a group of agents) and gram g:
#   y_U   = # of U's docs containing g,  n_U = # of U's docs
#   r_bg  = sum_w (n_Uw / n_U) * (T_w(g) - A_Uw(g)) / (N_w - n_Uw)
#           i.e. the rest-of-village rate, reweighted to U's weekly mix
#   N_bg  = sum_w (N_w - n_Uw),  y_bg = r_bg * N_bg
#   prior a_g = A0 * p_global(g)
#   delta = logit((y_U+a)/(n_U+A0)) - logit((y_bg+a)/(N_bg+A0))
#   z     = delta / sqrt(1/(y_U+a) + 1/(n_U-y_U+A0-a) + 1/(y_bg+a) + 1/(N_bg-y_bg+A0-a))
import polars as pl

A0 = 1000.0
DIR = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/tics/"
CORP = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/"


def load(src):
    c = pl.read_parquet(DIR + f"ng_{src}_counts.parquet")
    v = pl.read_parquet(DIR + f"ng_{src}_vocab.parquet")
    d = pl.read_parquet(DIR + f"ng_{src}_docs.parquet")
    wk = pl.col("day").dt.truncate("1w").alias("week")
    c = c.with_columns(wk)
    d = d.with_columns(wk)
    return c, v, d


def meta():
    m = (pl.read_parquet(CORP + "chat_raw.parquet", columns=["agent", "kind", "lab", "family", "cohort"])
         .filter(pl.col("kind") == "agent").drop("kind").unique("agent"))
    return m


def logodds(c, d, members, min_y=8):
    """c: (agent, day, week, h, c); d: (agent, day, week, docs); members: list of agents."""
    cw = c.group_by("week", "h").agg(pl.col("c").sum().alias("T"))
    dw = d.group_by("week").agg(pl.col("docs").sum().alias("N"))
    tot_docs = d["docs"].sum()
    pglob = c.group_by("h").agg((pl.col("c").sum() / tot_docs).alias("p"))
    uc = c.filter(pl.col("agent").is_in(members))
    ud = d.filter(pl.col("agent").is_in(members))
    uw = ud.group_by("week").agg(pl.col("docs").sum().alias("n"))
    n_U = uw["n"].sum()
    yU = uc.group_by("h").agg(pl.col("c").sum().alias("y"),
                              pl.col("day").n_unique().alias("days"),
                              pl.col("week").n_unique().alias("weeks"),
                              pl.col("agent").n_unique().alias("n_members_using"))
    yU = yU.filter(pl.col("y") >= min_y)
    mws = (uc.join(yU.select("h"), on="h", how="semi").group_by("h", "week").agg(pl.col("c").sum())
           .group_by("h").agg(pl.col("c").max().alias("maxw")))
    yU = yU.join(mws, on="h").with_columns((pl.col("maxw") / pl.col("y")).alias("max_week_share")).drop("maxw")
    A = uc.join(yU.select("h"), on="h", how="semi").group_by("week", "h").agg(pl.col("c").sum().alias("A"))
    w = uw.join(dw, on="week").filter(pl.col("N") > pl.col("n"))
    w = w.with_columns((pl.col("n") / pl.col("n").sum()).alias("wt"))
    N_bg = (w["N"] - w["n"]).sum()
    # background over U's weeks for U's grams
    bg = (cw.join(w.select("week", "wt", "N", "n"), on="week")
          .join(yU.select("h"), on="h", how="semi")
          .join(A, on=["week", "h"], how="left").with_columns(pl.col("A").fill_null(0))
          .group_by("h").agg((pl.col("wt") * (pl.col("T") - pl.col("A")) / (pl.col("N") - pl.col("n"))).sum().alias("r_bg")))
    out = (yU.join(bg, on="h", how="left").with_columns(pl.col("r_bg").fill_null(0.0))
           .join(pglob, on="h")
           .with_columns(a=A0 * pl.col("p"), y_bg=pl.col("r_bg") * N_bg))
    a, y, yb = pl.col("a"), pl.col("y"), pl.col("y_bg")
    out = out.with_columns(
        delta=((y + a) / (n_U - y + A0 - a)).log() - ((yb + a) / (N_bg - yb + A0 - a)).log(),
        var=1 / (y + a) + 1 / (n_U - y + A0 - a) + 1 / (yb + a) + 1 / (N_bg - yb + A0 - a),
        rate_1k=1000 * y / n_U, bg_1k=1000 * pl.col("r_bg"),
    ).with_columns(z=pl.col("delta") / pl.col("var").sqrt(),
                   ratio=(pl.col("rate_1k") + 0.05) / (pl.col("bg_1k") + 0.05))
    return out.drop("var", "a"), n_U


def prune_subsumed(df, v):
    """Drop a gram if a longer gram containing it (in this unit's table) has >= 80% of its count."""
    df = df.join(v, on="h")
    rows = df.sort("n", descending=True).select("g", "y", "n").rows()
    longer = {}
    keep = []
    for g, y, n in rows:
        sub = False
        for G, Y in longer.items():
            if Y >= 0.8 * y and f" {g} " in f" {G} ":
                sub = True
                break
        if not sub:
            longer[g] = y
            keep.append(g)
    return df.filter(pl.col("g").is_in(keep))
