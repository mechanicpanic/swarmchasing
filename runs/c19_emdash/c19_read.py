"""C19 follow-ups: (1) the days between Opus 4.6's arrival and the nudger's first
message; (2) are onset-week em-dashes copied from a 4.6 agent or the nudger, or
quoted; a sample to read; (3) within-week dose: does an incumbent's weekly rate
follow the 4.6 share of the rooms it talked in, with agent and week effects
removed? Null: that share permuted across agents within the same week.

usage: REPO=... OUT=... python runs/c19_emdash/c19_read.py
"""

import os

import numpy as np
import polars as pl

REPO = os.environ.get("REPO", ".")
OUT = os.environ.get("OUT", "results/c19")
NEW = ["Claude Opus 4.6", "Claude Sonnet 4.6"]
INC = ["Claude Haiku 4.5", "Claude Opus 4.5", "Claude Sonnet 4.5", "DeepSeek-V3.2"]
INC += ["GPT-5", "GPT-5.1", "GPT-5.2", "Gemini 2.5 Pro", "Gemini 3 Pro", "Claude 3.7 Sonnet"]
EM = " — "


def T(*a):
    return pl.datetime(*a, time_zone="UTC")


d = (
    pl.scan_parquet(f"{REPO}/data/village.parquet")
    .filter(pl.col("kind").is_in(["AGENT_TALK", "USER_TALK"]))
    .select("id", "time", "kind", "agent", "room", "text")
    .collect()
    .sort("time")
    .with_columns(pl.col("text").str.contains(EM, literal=True).alias("em"), pl.col("time").dt.truncate("1w").alias("w"))
)
talk = d.filter(pl.col("kind") == "AGENT_TALK").unique(["agent", "text"], keep="first", maintain_order=True)
nudge = d.filter(pl.col("agent") == "automated")

# (1) the days between arrivals -----------------------------------------------
t_new = talk.filter(pl.col("agent") == "Claude Opus 4.6")["time"].min()
t_nudge = nudge.filter(pl.col("time") > T(2026, 2, 1), pl.col("em"))["time"].min()
print(f"first Opus 4.6 message {t_new}; first nudger em-dash message {t_nudge}")
win = [("Jan 05-Feb 05", T(2026, 1, 5), T(2026, 2, 6)), ("4.6 before nudger", t_new, t_nudge), ("nudger to Feb 15", t_nudge, T(2026, 2, 16))]
rows = []
for lbl, a, b in win:
    s = talk.filter(pl.col("agent").is_in(INC), pl.col("time") >= a, pl.col("time") < b)
    rows.append(s.group_by("agent").agg(pl.len().alias("n"), pl.col("em").sum().alias("k")).with_columns(pl.lit(lbl).alias("win")))
sub = pl.concat(rows)
pl.Config.set_tbl_rows(60)
pl.Config.set_tbl_width_chars(220)
pl.Config.set_fmt_str_lengths(200)
print(sub.with_columns((pl.col("k") / pl.col("n")).round(3).alias("rate")).pivot(on="win", index="agent", values=["n", "rate"]))
print("pooled:", sub.group_by("win").agg(pl.col("n").sum(), pl.col("k").sum()).with_columns((pl.col("k") / pl.col("n")).round(3).alias("rate")))

# (2) copied or own prose in onset weeks ----------------------------------------
onsets = {"Claude Haiku 4.5": "2026-02-09", "Claude Opus 4.5": "2026-02-16", "DeepSeek-V3.2": "2026-02-16"}
onsets |= {"GPT-5.1": "2026-03-02", "GPT-5.2": "2026-03-09", "Claude Sonnet 4.5": "2026-02-16", "Gemini 3 Pro": "2026-02-16"}
src = pl.concat([talk.filter(pl.col("agent").is_in(NEW)), nudge]).filter(pl.col("em")).sort("time")
src_t, src_x = src["time"].to_list(), src["text"].to_list()
uses = []
for a, w in onsets.items():
    w0 = np.datetime64(w)
    m = talk.filter(pl.col("agent") == a, pl.col("em"), pl.col("w").dt.date().is_between(w0, w0 + np.timedelta64(7, "D")))
    for i, t, x in m.select("id", "time", "text").iter_rows():
        pool = "\x00".join(s for st, s in zip(src_t, src_x) if st < t)
        ctx = []
        for j in [k for k in range(len(x)) if x.startswith(EM, k)]:
            c = x[max(0, j - 15) : j + 18]
            ctx.append(c)
        copied = any(len(c) >= 30 and c in pool for c in ctx)
        quoted = any(('"' in x[max(0, j - 80) : j] and '"' in x[j : j + 80]) for j in [x.find(EM)])
        uses.append({"agent": a, "id": i, "time": t, "copied": copied, "in_quotes": quoted, "snip": x[max(0, x.find(EM) - 70) : x.find(EM) + 70]})
u = pl.DataFrame(uses)
print(u.group_by("agent").agg(pl.len(), pl.col("copied").sum(), pl.col("in_quotes").sum()).sort("agent"))
print("total", u.height, "copied", u["copied"].sum(), "in quotes", u["in_quotes"].sum())
samp = u.group_by("agent").map_groups(lambda g: g.sample(min(3, g.height), seed=7)).sort("time")
samp.write_csv(f"{OUT}/onset_sample.csv")
for r in samp.iter_rows(named=True):
    print(f"{r['time']:%m-%d %H:%M} {r['agent'][:16]:16s} {r['id'][:8]} c={int(r['copied'])} q={int(r['in_quotes'])} …{r['snip']!r}")

# (3) within-week dose ------------------------------------------------------------
p = talk.filter(pl.col("time").is_between(T(2026, 2, 23), T(2026, 6, 29)))
room_w = p.group_by("w", "room").agg(pl.len().alias("rn"), pl.col("agent").is_in(NEW).sum().alias("rnew"))
mine = p.filter(pl.col("agent").is_in(INC)).group_by("agent", "w", "room").agg(pl.len().alias("an"), pl.col("em").sum().alias("ak"))
mine = mine.join(room_w, on=["w", "room"]).with_columns(((pl.col("rnew")) / (pl.col("rn") - pl.col("an")).clip(1)).alias("share"))
aw = (
    mine.group_by("agent", "w")
    .agg(pl.col("an").sum().alias("n"), pl.col("ak").sum().alias("k"), (pl.col("share") * pl.col("an")).sum().alias("sx"))
    .filter(pl.col("n") >= 15)
    .with_columns((pl.col("k") / pl.col("n")).alias("y"), (pl.col("sx") / pl.col("n")).alias("x"))
    .sort("agent", "w")
)
ai = aw["agent"].cast(pl.Categorical).to_physical().to_numpy()
wi = aw["w"].rank("dense").cast(pl.Int64).to_numpy() - 1


def demean(v):
    v = v.astype(float).copy()
    for _ in range(100):
        v -= (np.bincount(ai, v) / np.bincount(ai))[ai]
        v -= (np.bincount(wi, v) / np.bincount(wi))[wi]
    return v


y, x = demean(aw["y"].to_numpy()), aw["x"].to_numpy()
xd = demean(x)
beta = (xd @ y) / (xd @ xd)
rng = np.random.default_rng(0)
null = []
for _ in range(2000):
    xp = x.copy()
    for g in np.unique(wi):
        idx = np.where(wi == g)[0]
        xp[idx] = rng.permutation(xp[idx])
    xpd = demean(xp)
    null.append((xpd @ y) / (xpd @ xpd))
null = np.array(null)
print(f"dose: {aw.height} agent-weeks, {len(np.unique(wi))} weeks; within-week sd of x {np.mean([x[wi == g].std() for g in np.unique(wi)]):.3f}")
print(f"beta {beta:.3f} (rate per unit 4.6 share); null mean {null.mean():.3f} sd {null.std():.3f}; p(null>=obs) {(null >= beta).mean():.4f}")
print(aw.group_by("agent").agg(pl.col("x").mean().round(3), pl.col("y").mean().round(3), pl.len()).sort("agent"))

# (4) hour scale, day-stratified: an incumbent's message after a 4.6 em-dash in the
# same room (60 min) vs after a 4.6 message with no em-dash (the twin: presence
# without the style) vs after the nudger's em-dash. Mantel-Haenszel RR by (agent, day).
H = pl.duration(minutes=int(os.environ.get("WIN_MIN", "60")))
per = (T(2026, 2, 6), T(2026, 3, 23))
inc = talk.filter(pl.col("agent").is_in(INC), pl.col("time").is_between(*per)).select("time", "agent", "room", "em").sort("time")
inc = inc.with_columns(pl.col("time").dt.date().alias("day"))


srcs = {
    "after_4.6_em": talk.filter(pl.col("agent").is_in(NEW), pl.col("em")),
    "after_4.6_noem": talk.filter(pl.col("agent").is_in(NEW), ~pl.col("em")),
    "after_nudger_em": nudge.filter(pl.col("em")),
}
for name, s in srcs.items():
    s = s.select("room", pl.col("time").alias("t_src")).sort("t_src")
    inc = inc.join_asof(s, left_on="time", right_on="t_src", by="room", strategy="backward")
    inc = inc.with_columns(((pl.col("time") - pl.col("t_src")) <= H).fill_null(False).alias(name)).drop("t_src")


def mh(df, flag):
    g = df.group_by("agent", "day").agg(
        (pl.col(flag) & pl.col("em")).sum().alias("a"), pl.col(flag).sum().alias("n1"),
        (~pl.col(flag) & pl.col("em")).sum().alias("c"), (~pl.col(flag)).sum().alias("n0"),
    ).with_columns((pl.col("n1") + pl.col("n0")).alias("N"))
    num = (g["a"] * g["n0"] / g["N"]).sum()
    den = (g["c"] * g["n1"] / g["N"]).sum()
    return round(num / den, 2) if den else None, int(df[flag].sum())


for name in srcs:
    rr, k = mh(inc, name)
    rr_x, _ = mh(inc.filter(~pl.col("agent").str.starts_with("Claude")), name)
    print(f"{name:16s} exposed msgs {k:5d}  MH RR all {rr}  non-Anthropic {rr_x}")

days = inc["day"].unique().sort().to_list()
rng = np.random.default_rng(1)
print(f"incumbent msgs 2026-02-06..03-23: {inc.height}; window {H}")
for name in ["after_4.6_em", "after_4.6_noem"]:
    for grp, df in [("all", inc), ("Anthropic", inc.filter(pl.col("agent").str.starts_with("Claude"))), ("non-Anthropic", inc.filter(~pl.col("agent").str.starts_with("Claude")))]:
        bs = []
        for _ in range(300):  # bootstrap over days
            pick = pl.DataFrame({"day": [days[i] for i in rng.integers(0, len(days), len(days))]}, schema={"day": pl.Date}).with_row_index("rep")
            r, _ = mh(df.join(pick, on="day").with_columns(pl.concat_str(pl.col("day").cast(pl.Utf8), pl.col("rep").cast(pl.Utf8)).alias("day")), name)
            if r:
                bs.append(r)
        print(f"{name:16s} {grp:14s} RR {mh(df, name)[0]}  95% day-bootstrap {np.percentile(bs, 2.5):.2f}-{np.percentile(bs, 97.5):.2f}")
for a in INC:
    sub_a = inc.filter(pl.col("agent") == a)
    if sub_a.height:
        print(f"  {a:18s} n {sub_a.height:5d} RR 4.6-em {mh(sub_a, 'after_4.6_em')[0]}  twin {mh(sub_a, 'after_4.6_noem')[0]}")
