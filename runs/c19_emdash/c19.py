"""C19: did the spaced em-dash (" — ") spread from the Claude 4.6 agents to older agents?

Per incumbent agent and stream (AGENT_TALK, THOUGHT): weekly rate of messages with a
spaced em-dash; the onset week by a trailing-baseline rule; the week of first
exposure to a 4.6 agent in the same room; the nearest CHANGELOG date. Null: the
exposure week shifted by +-1..8 weeks (common shift, and independent per-agent
shifts), the agent's own series fixed.

The server's text predicate drops punctuation (contains_phrase(" — ") counts 0,
no warning), so the text work is polars on the same Parquet the server reads.

usage: REPO=... OUT=... python runs/c19_emdash/c19.py [k]
"""

import os
import re
import sys

import numpy as np
import polars as pl

REPO = os.environ.get("REPO", ".")
OUT = os.environ.get("OUT", "results/c19")
K = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
MIN_N, BASE_W, MIN_BASE, FLOOR = 15, 8, 4, 0.05  # msgs/week, trailing weeks, min weeks, abs rise
NEW = ["Claude Opus 4.6", "Claude Sonnet 4.6"]
LAB = {"Claude": "Anthropic", "GPT": "OpenAI", "Gemini": "Google", "DeepSeek": "DeepSeek"}
T_EXPOSE = pl.datetime(2026, 2, 2, time_zone="UTC")  # week of Opus 4.6's first message
SEARCH = (pl.datetime(2025, 11, 3, time_zone="UTC"), pl.datetime(2026, 6, 29, time_zone="UTC"))
CLASSES = {  # message-level indicators
    "sp_em": r" — ",
    "unsp_em": r"\S—\S",
    "sp_hy": r"\S - \S",
    "dbl_hy": r" -- ",
}

os.makedirs(OUT, exist_ok=True)
raw = (
    pl.scan_parquet(f"{REPO}/data/village.parquet")
    .filter(pl.col("kind").is_in(["AGENT_TALK", "THOUGHT"]))
    .select("id", "time", "kind", "agent", "room", "text")
    .collect()
    .unique(["agent", "kind", "text"], keep="first", maintain_order=True)
    .with_columns(pl.col("time").dt.truncate("1w").alias("w"))
    .with_columns(pl.col("text").str.contains(p).alias(c) for c, p in CLASSES.items())
)


def lab(a):
    return next((v for k, v in LAB.items() if a.startswith(k) or a.startswith("Opus")), "?")


weekly = raw.group_by("agent", "kind", "w").agg(
    pl.len().alias("n"), *[pl.col(c).mean().alias(c) for c in CLASSES]
)
talk_w = weekly.filter(pl.col("kind") == "AGENT_TALK", pl.col("n") >= MIN_N)
inc = (
    talk_w.group_by("agent")
    .agg(
        (pl.col("w") < T_EXPOSE).sum().alias("pre"),
        (pl.col("w") >= T_EXPOSE).sum().alias("post"),
    )
    .filter(pl.col("pre") >= MIN_BASE + 1, pl.col("post") >= 2, ~pl.col("agent").is_in(NEW))
    .sort("agent")["agent"]
    .to_list()
)


def onset(series, k=K):
    """series: sorted list of (week, rate). First week whose rate and the next
    qualifying week's rate both exceed max(mean + k*sd, mean + FLOOR) of the
    trailing BASE_W qualifying weeks (at least MIN_BASE)."""
    for i in range(MIN_BASE, len(series) - 1):
        w, r = series[i]
        if not (SEARCH_LO <= w <= SEARCH_HI):
            continue
        base = np.array([x for _, x in series[max(0, i - BASE_W) : i]])
        thr = max(base.mean() + k * base.std(ddof=1), base.mean() + FLOOR)
        if r > thr and series[i + 1][1] > thr:
            return w, base.mean(), base.std(ddof=1), thr
    return None, None, None, None


SEARCH_LO, SEARCH_HI = pl.select(SEARCH[0]).item(), pl.select(SEARCH[1]).item()
T_EXPOSE_DT = pl.select(T_EXPOSE).item()

# exposure: first week a 4.6 agent talked in a room the agent talked in that week
talk = raw.filter(pl.col("kind") == "AGENT_TALK")
new_rooms = talk.filter(pl.col("agent").is_in(NEW)).select("w", "room").unique()
expo = (
    talk.filter(pl.col("agent").is_in(inc))
    .select("agent", "w", "room")
    .unique()
    .join(new_rooms, on=["w", "room"])
    .group_by("agent")
    .agg(pl.col("w").min().alias("expo"))
)
expo = dict(expo.iter_rows())

# CHANGELOG dates (a range heading counts by its first day)
cl = {}
title = None
for line in open(f"{REPO}/data/village/CHANGELOG.md"):
    m = re.match(r"## (\d{4}-\d{2}-\d{2})", line)
    if m:
        title = m.group(1)
        cl[title] = ""
    elif title and line.startswith("- ") and not cl[title]:
        cl[title] = line[2:].strip()[:90]
cl_dates = np.array(sorted(np.datetime64(d) for d in cl))


def nearest_cl(w):
    w = np.datetime64(w.date())
    i = np.argmin(np.abs(cl_dates - w))
    d = cl_dates[i]
    return str(d), int((d - w) / np.timedelta64(1, "D")), cl[str(d)]


rows = []
for kind in ["AGENT_TALK", "THOUGHT"]:
    for a in inc:
        s = (
            weekly.filter(pl.col("agent") == a, pl.col("kind") == kind, pl.col("n") >= MIN_N)
            .sort("w")
            .select("w", "sp_em")
            .rows()
        )
        if len(s) < MIN_BASE + 2:
            continue
        pre = [r for w, r in s if w < T_EXPOSE_DT]
        pre8 = pre[-8:]
        w0, bm, bs, thr = onset(s)
        e = expo.get(a)
        rec = {
            "kind": kind,
            "agent": a,
            "lab": lab(a),
            "pre8_rate": round(float(np.mean(pre8)), 3) if pre8 else None,
            "onset": w0.date().isoformat() if w0 else None,
            "base_mean": None if bm is None else round(bm, 3),
            "base_sd": None if bs is None else round(bs, 3),
            "thr": None if thr is None else round(thr, 3),
            "onset_rate": None if w0 is None else round(dict(s)[w0], 3),
            "expo": e.date().isoformat() if e else None,
            "lag_weeks": None if (w0 is None or e is None) else (w0 - e).days // 7,
        }
        if w0:
            rec["cl_date"], rec["cl_days"], rec["cl_what"] = nearest_cl(w0)
        rows.append(rec)
tab = pl.DataFrame(rows)
tab.write_csv(f"{OUT}/onsets_k{K:g}.csv")
pl.Config.set_tbl_rows(40)
pl.Config.set_tbl_cols(20)
pl.Config.set_tbl_width_chars(260)
pl.Config.set_fmt_str_lengths(60)
print(f"incumbents: {inc}\nk={K}")
print(tab.drop("cl_what", "base_sd", "thr"))


def nulls(lags, wins=(0, 2), n_draw=10000, seed=0):
    """lags: onset - exposure in weeks (None = no onset). Statistic: onsets within
    [wins[0], wins[1]] weeks after exposure. Common shift and independent shifts."""
    lags = [x for x in lags]
    obs = sum(x is not None and wins[0] <= x <= wins[1] for x in lags)
    shifts = [s for s in range(-8, 9) if s != 0]
    common = [sum(x is not None and wins[0] <= x - s <= wins[1] for x in lags) for s in shifts]
    rng = np.random.default_rng(seed)
    draws = rng.choice(shifts, size=(n_draw, len(lags)))
    lag_arr = np.array([np.nan if x is None else x for x in lags], dtype=float)
    shifted = lag_arr[None, :] - draws
    ind = ((shifted >= wins[0]) & (shifted <= wins[1])).sum(axis=1)
    return {
        "n_agents": len(lags),
        "n_onsets": sum(x is not None for x in lags),
        "obs": obs,
        "common_shift_mean": round(float(np.mean(common)), 2),
        "common_shift_max": int(max(common)),
        "p_common": round((1 + sum(c >= obs for c in common)) / (1 + len(common)), 3),
        "common_by_shift": dict(zip(shifts, common)),
        "indep_mean": round(float(ind.mean()), 2),
        "p_indep": round(float((ind >= obs).mean()), 4),
    }


for kind in ["AGENT_TALK", "THOUGHT"]:
    t = tab.filter(pl.col("kind") == kind)
    for grp, sub in [("all", t), ("non-Anthropic", t.filter(pl.col("lab") != "Anthropic"))]:
        print(kind, grp, nulls(sub["lag_weeks"].to_list()))

# scaffold competitors: onsets falling 0..2 weeks after a named CHANGELOG change
for name, d in [("nudger 02-10", "2026-02-09"), ("rooms v1 02-25", "2026-02-23"), ("perma-CU 03-24", "2026-03-23")]:
    t = tab.filter(pl.col("kind") == "AGENT_TALK", pl.col("onset").is_not_null())
    lag = [(np.datetime64(o) - np.datetime64(d)) // np.timedelta64(7, "D") for o in t["onset"]]
    print(f"AGENT_TALK onsets 0..2 wk after {name}: {sum(0 <= x <= 2 for x in lag)} of {t.height}")

# other dash forms, same agents: Jan 5 - Feb 5 vs Feb 9 - Mar 15 (AGENT_TALK)
per = {"pre": (pl.datetime(2026, 1, 5, time_zone="UTC"), pl.datetime(2026, 2, 6, time_zone="UTC")),
       "post": (pl.datetime(2026, 2, 9, time_zone="UTC"), pl.datetime(2026, 3, 16, time_zone="UTC"))}
forms = pl.concat(
    raw.filter(pl.col("kind") == "AGENT_TALK", pl.col("agent").is_in(inc + NEW), pl.col("time").is_between(*b))
    .group_by("agent").agg(pl.len().alias("n"), *[(100 * pl.col(c).mean()).round(1).alias(c) for c in CLASSES])
    .with_columns(pl.lit(k).alias("per"))
    for k, b in per.items()
).sort("agent", "per", descending=[False, True])
print(forms)
