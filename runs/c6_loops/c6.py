"""C6: verbatim loops. Runs of >= 5 identical AGENT_TALK messages by one agent, each within 30 min of the previous one
(the server's RUN(field(kind, AGENT_TALK) AND field(agent, $a) AND field(text, $t)){5,} DURING 30 minutes, label
talk-same-text-run5), reimplemented on the parquet so it can be varied and nulled.
Sections:
  1 reproduce: per-agent run counts (exact text) — must equal the server's grouped_values
  2 semantics: what lies between a run's first and last message (other agents' talk, the agent's own other talk),
    and the same counts when a run must be consecutive among the agent's own talk / in the whole talk stream
  3 near-identical: text with whitespace collapsed; and a looser key (lowercase, digits and punctuation stripped)
  4 rates: talk, runs, runs per 1,000 talk, messages in runs, share of runs vs share of talk; the twin (RUN without
    field(text, $t): any >= 5 own talks, each within 30 min) per agent
  5 nulls for "Gemini 2.5 Pro loops more than its share of talk":
    (a) same-day allocation: each day's runs are re-assigned to that day's talkers in proportion to their talk that day
        (multinomial, n draws); breaks only who looped, keeps how many loops each day had
    (b) day-block bootstrap of Gemini's rate ratio (its runs per talk / everyone else's), days resampled with replacement
    (c) per agent vs the others on the same days: an agent's runs/1k talk against the pooled others' runs/1k on the
        days that agent talked
  6 Gemini 2.5 Pro timeline: runs by month, distinct texts, top re-sent texts, run lengths, what its own non-talk rows
    between loop messages are; distress/frame words in loop texts vs its other talk, by month; standby/blocked words
  7 mechanism: P(an agent's next talk is identical | its own talk -> its own WAIT -> its own talk), per agent, the
    same with no WAIT between, and Gemini 2.5 Pro vs the others on the same days
usage (repo root): REPO=. .venv/bin/python runs/c6_loops/c6.py [--n 2000] [--only-sections 1,2,...]"""
import argparse, os, re
from collections import Counter
import numpy as np
import polars as pl

R = os.environ.get("REPO", ".") + "/"
VILLAGE = os.environ.get("VILLAGE", R + "data/village.parquet")
GAP = 30 * 60 * 1_000_000  # 30 min in us
G = "Gemini 2.5 Pro"
SERVER = {G: 253, "Grok 4": 22, "o3": 8, "Claude Opus 4.1": 4, "Gemini 3 Pro": 4, "Claude 3.7 Sonnet": 2,
          "Claude Haiku 4.5": 1, "[Temporary] Fine-tuned Leader": 1}  # label talk-same-text-run5, 2026-10-04
DISTRESS = re.compile(r"(?i)\b(fail\w*|stuck|unable|cannot|can't|hope|plea|desperat\w*|broken|blocked|error|404|"
                      r"impossible|frustrat\w*|give up|giving up)\b")
STAND = (r"(?i)\b(wait\w*|stand(ing)? by|standby|silence|monitor\w*|observ\w*|idle|await\w*|completed?|no further|"
         r"remain\w* on|pause|hold\w*)\b")
BLOCK = (r"(?i)\b(block\w*|fail\w*|error\w*|bug\w*|unable|cannot|can't|stuck|broken|terminat\w*|crash\w*|404|frozen|"
         r"unresponsive|hope|plea)\b")
FRAME = re.compile(r"(?i)hostil\w*|adversar\w*|divergent realit\w*|dual realit\w*|friction coefficient|broken world|"
                   r"gemini wall")


def runs(df, key, gap=GAP, k=5):
    """Maximal chains of rows sharing `key` (+agent), each within `gap` of the previous; returns rows with run_id, len."""
    d = df.sort("t").with_columns(
        ((pl.col("t") - pl.col("t").shift(1).over(["agent", key])) > gap).fill_null(True).alias("brk"))
    d = d.with_columns(pl.col("brk").cast(pl.Int32).cum_sum().over(["agent", key]).alias("chain"))
    d = d.with_columns(pl.len().over(["agent", key, "chain"]).alias("rlen"))
    d = d.filter(pl.col("rlen") >= k)
    return d.with_columns(pl.struct(["agent", key, "chain"]).hash(seed=0).alias("run_id"))


def per_agent(r):
    return r.group_by("agent").agg(pl.col("run_id").n_unique().alias("runs"), pl.len().alias("msgs"))


def consecutive_runs(df, scope, k=5, gap=GAP):
    """Runs of identical text that are consecutive in `scope` ('own': the agent's own talk; 'all': all talk)."""
    d = df.sort("t")
    over = ["agent"] if scope == "own" else []
    prev_t = pl.col("text").shift(1).over(over) if over else pl.col("text").shift(1)
    prev_a = pl.col("agent").shift(1).over(over) if over else pl.col("agent").shift(1)
    prev_time = pl.col("t").shift(1).over(over) if over else pl.col("t").shift(1)
    d = d.with_columns(((pl.col("text") != prev_t) | (pl.col("agent") != prev_a) | ((pl.col("t") - prev_time) > gap))
                       .fill_null(True).alias("brk"))
    cs = pl.col("brk").cast(pl.Int32).cum_sum()
    d = d.with_columns((cs.over(over) if over else cs).alias("chain"))
    d = d.with_columns(pl.len().over(["agent", "chain"]).alias("rlen")).filter(pl.col("rlen") >= k)
    return d.group_by("agent").agg(pl.col("chain").n_unique().alias("runs"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--only-sections", default="1,2,3,4,5,6,7")
    a = ap.parse_args()
    S = set(a.only_sections.split(","))
    allrows = pl.read_parquet(VILLAGE, columns=["id", "time", "kind", "agent", "text"])
    allrows = allrows.with_columns(pl.col("time").dt.epoch("us").alias("t"), pl.col("time").dt.date().alias("day"))
    talk = allrows.filter((pl.col("kind") == "AGENT_TALK") & pl.col("agent").is_not_null() & pl.col("text").is_not_null())
    talk = talk.with_columns(
        pl.col("text").str.replace_all(r"\s+", " ").str.strip_chars().alias("ws"),
        pl.col("text").str.to_lowercase().str.replace_all(r"[\d\W_]+", " ").str.strip_chars().alias("loose"))
    r_exact = runs(talk, "text")
    pa = per_agent(r_exact).sort("runs", descending=True)

    if "1" in S:
        print("== 1 reproduce (exact text) ==")
        mine = dict(zip(pa["agent"], pa["runs"]))
        print(pa)
        print("matches server:", mine == SERVER, "| total", sum(mine.values()))

    if "2" in S:
        print("\n== 2 semantics ==")
        spans = r_exact.group_by("run_id").agg(pl.col("agent").first(), pl.col("t").min().alias("t0"),
                                               pl.col("t").max().alias("t1"), pl.col("text").first(),
                                               pl.len().alias("n"))
        tk = talk.select("t", "agent", "text").sort("t")
        ts = tk["t"].to_numpy()
        other, own_other = 0, 0
        for row in spans.iter_rows(named=True):
            lo, hi = np.searchsorted(ts, row["t0"], "left"), np.searchsorted(ts, row["t1"], "right")
            seg = tk.slice(lo, hi - lo)
            other += int((seg["agent"] != row["agent"]).any())
            own_other += int(((seg["agent"] == row["agent"]) & (seg["text"] != row["text"])).any())
        print(f"runs {spans.height}: with other agents' talk inside {other}; with the agent's own different talk "
              f"inside {own_other}")
        for scope in ("own", "all"):
            c = consecutive_runs(talk, scope).sort("runs", descending=True)
            print(f"consecutive in {scope} talk:", dict(zip(c["agent"], c["runs"])))
        span_min = (spans["t1"] - spans["t0"]) / 6e7
        print("run span minutes: median %.1f, 90th %.1f, max %.1f; run length median %d max %d" % (
            span_min.median(), span_min.quantile(0.9), span_min.max(), spans["n"].median(), spans["n"].max()))
        gs = spans.filter(pl.col("agent") == G)
        print(f"{G}: span median {((gs['t1'] - gs['t0']) / 6e7).median():.1f} min")

    if "3" in S:
        print("\n== 3 near-identical ==")
        for key in ("ws", "loose"):
            p = per_agent(runs(talk, key)).sort("runs", descending=True)
            print(key, dict(zip(p["agent"], p["runs"])), "total", p["runs"].sum())

    tot = talk.group_by("agent").agg(pl.len().alias("talk"))
    if "4" in S:
        print("\n== 4 rates and twin ==")
        tw = runs(talk.with_columns(pl.lit(1).alias("any")), "any")
        ptw = per_agent(tw).rename({"runs": "twin_runs", "msgs": "twin_msgs"})
        t4 = (tot.join(pa, on="agent", how="left").join(ptw, on="agent", how="left").fill_null(0)
              .with_columns((pl.col("runs") / pl.col("talk") * 1000).round(2).alias("runs_per_1k"),
                            (pl.col("talk") / pl.col("talk").sum() * 100).round(1).alias("talk_%"),
                            (pl.col("runs") / pl.col("runs").sum() * 100).round(1).alias("runs_%"),
                            (pl.col("twin_runs") / pl.col("twin_runs").sum() * 100).round(1).alias("twin_%"),
                            (pl.col("twin_runs") / pl.col("talk") * 1000).round(1).alias("twin_per_1k"))
              .sort(["runs", "talk"], descending=True))
        with pl.Config(tbl_rows=12, tbl_cols=12, tbl_width_chars=200):
            print(t4.head(12))
        print("twin totals:", t4["twin_runs"].sum(), "runs; corr(twin share, talk share) =",
              round(float(np.corrcoef(t4["twin_%"], t4["talk_%"])[0, 1]), 3))

    if "5" in S:
        print("\n== 5 nulls ==")
        rstart = r_exact.group_by("run_id").agg(pl.col("agent").first(), pl.col("day").first())
        dr = rstart.group_by("day").agg(pl.len().alias("R"))
        dt = talk.group_by(["day", "agent"]).agg(pl.len().alias("n"))
        rg = rstart.group_by(["day", "agent"]).agg(pl.len().alias("r"))
        dd = dt.join(rg, on=["day", "agent"], how="left").fill_null(0)
        days = sorted(dd["day"].unique().to_list())
        rng = np.random.default_rng(6)
        # (a) same-day allocation
        realG = int(rstart.filter(pl.col("agent") == G).height)
        sims = np.zeros(a.n, dtype=int)
        expG = 0.0
        Rmap = dict(zip(dr["day"], dr["R"]))
        for day in days:
            R_ = Rmap.get(day, 0)
            if not R_: continue
            sub = dd.filter(pl.col("day") == day).sort("agent")
            p = (sub["n"] / sub["n"].sum()).to_numpy()
            gi = sub["agent"].to_list().index(G) if G in sub["agent"].to_list() else None
            if gi is None: continue
            expG += R_ * p[gi]
            sims += rng.binomial(R_, p[gi], size=a.n)
        print(f"(a) same-day allocation: {G} real {realG}, null mean {sims.mean():.1f} (exp {expG:.1f}), 95th "
              f"{np.percentile(sims, 95):.0f}, max {sims.max()}, p(>= real) = {(sims >= realG).mean():.4f} (n={a.n})")
        # (a') runs cluster by day: give each day's runs to one agent as a block, and count looping days (cold check)
        Rd, pG = [], []
        for day in days:
            sub = dd.filter(pl.col("day") == day)
            if not Rmap.get(day) or G not in sub["agent"].to_list(): continue
            Rd.append(Rmap[day]); pG.append(sub.filter(pl.col("agent") == G)["n"].item() / sub["n"].sum())
        Rd, pG = np.array(Rd), np.array(pG)
        hit = rng.random((a.n, len(Rd))) < pG
        blk, dys = (hit * Rd).sum(1), hit.sum(1)
        realD = rstart.filter(pl.col("agent") == G)["day"].n_unique()
        print(f"(a') day-block: {G} real {realG}, null mean {blk.mean():.1f}, 95th {np.percentile(blk, 95):.0f}, max {blk.max()}, "
              f"p {(blk >= realG).mean():.4f}; looping days real {realD} of {len(Rd)}, null mean {dys.mean():.1f}, "
              f"95th {np.percentile(dys, 95):.0f}, p {(dys >= realD).mean():.4f}")
        # (b) day-block bootstrap of the rate ratio
        piv = dd.with_columns((pl.col("agent") == G).alias("g")).group_by(["day", "g"]).agg(
            pl.col("n").sum(), pl.col("r").sum()).sort("day")
        gd = piv.filter(pl.col("g")).select("day", pl.col("n").alias("gn"), pl.col("r").alias("gr"))
        od = piv.filter(~pl.col("g")).select("day", pl.col("n").alias("on"), pl.col("r").alias("or"))
        bd = od.join(gd, on="day", how="full", coalesce=True).fill_null(0).sort("day")
        bd = bd.filter(pl.col("gn") > 0)  # days Gemini 2.5 Pro talked
        M = bd.select("gr", "gn", "or", "on").to_numpy().astype(float)
        idx = rng.integers(0, len(M), size=(a.n, len(M)))
        S_ = M[idx].sum(axis=1)
        ratio = (S_[:, 0] / S_[:, 1]) / np.maximum(S_[:, 2], 0.5) * S_[:, 3]
        real_ratio = (M[:, 0].sum() / M[:, 1].sum()) / (M[:, 2].sum() / M[:, 3].sum())
        print(f"(b) on {len(M)} days {G} talked: its runs {M[:,0].sum():.0f} / talk {M[:,1].sum():.0f}; others "
              f"{M[:,2].sum():.0f} / {M[:,3].sum():.0f}; rate ratio {real_ratio:.1f}, day-block 95% CI "
              f"[{np.percentile(ratio, 2.5):.1f}, {np.percentile(ratio, 97.5):.1f}], share of draws <= 1: "
              f"{(ratio <= 1).mean():.4f}")
        gdays = bd.filter(pl.col("gr") > 0).sort("gr", descending=True)
        print(f"   {G}'s runs fall on {gdays.height} days; top 5 days carry {gdays['gr'].head(5).sum()} "
              f"({', '.join(f'{d}:{r}' for d, r in zip(gdays['day'].head(5), gdays['gr'].head(5)))})")
        # (c) every agent vs the others on its own days
        print(f"(c) agent: runs/1k on its days vs others' (without {G}) runs/1k on the same days")
        for ag in pa["agent"].head(6).to_list():
            mydays = dd.filter((pl.col("agent") == ag)).select("day")
            sub = dd.join(mydays, on="day")
            me = sub.filter(pl.col("agent") == ag)
            ot = sub.filter((pl.col("agent") != ag) & (pl.col("agent") != G))  # others, Gemini 2.5 Pro excluded
            print(f"   {ag:30s} {me['r'].sum():4d}/{me['n'].sum():6d} = {me['r'].sum()/me['n'].sum()*1000:6.2f}  vs "
                  f"{ot['r'].sum():4d}/{ot['n'].sum():6d} = {ot['r'].sum()/ot['n'].sum()*1000:5.2f}  over "
                  f"{mydays.height} days")

    if "6" in S:
        print(f"\n== 6 {G} timeline ==")
        gr = r_exact.filter(pl.col("agent") == G).with_columns(pl.col("time").dt.strftime("%Y-%m").alias("month"))
        gt = talk.filter(pl.col("agent") == G).with_columns(pl.col("time").dt.strftime("%Y-%m").alias("month"))
        gt = gt.with_columns(pl.col("id").is_in(gr["id"].implode()).alias("inloop"),
                             pl.col("text").str.contains(DISTRESS.pattern).alias("distress"),
                             pl.col("text").str.contains(FRAME.pattern).alias("frame"))
        m = gt.group_by("month").agg(
            pl.len().alias("talk"), pl.col("inloop").sum().alias("loop_msgs"),
            pl.col("frame").sum().alias("frame_msgs"),
            pl.col("distress").filter(pl.col("inloop")).mean().round(2).alias("distress_in_loops"),
            pl.col("distress").filter(~pl.col("inloop")).mean().round(2).alias("distress_other"))
        runsm = gr.group_by("run_id").agg(pl.col("month").first()).group_by("month").agg(pl.len().alias("runs"))
        m = m.join(runsm, on="month", how="left").fill_null(0).sort("month")
        with pl.Config(tbl_rows=30):
            print(m)
        spans = gr.group_by("run_id").agg(pl.col("text").first(), pl.len().alias("n"), pl.col("time").min().alias("t0"),
                                          pl.col("time").max().alias("t1"), pl.col("id").first().alias("id0"))
        print(f"runs {spans.height}, messages {gr.height}, distinct texts {spans['text'].n_unique()}, "
              f"run length median {spans['n'].median()}, max {spans['n'].max()}")
        tc = Counter(spans["text"].to_list())
        print("texts re-run in >1 run:", sum(1 for v in tc.values() if v > 1), "| top:",
              [(t[:70], c) for t, c in tc.most_common(4)])
        print("longest runs:")
        for row in spans.sort("n", descending=True).head(6).iter_rows(named=True):
            print(f"   {row['n']:3d}x {str(row['t0'])[:16]}–{str(row['t1'])[11:16]} {row['id0'][:8]} {row['text'][:80]!r}")
        # Gemini's own non-talk rows between the first and last message of each run
        own = allrows.filter(pl.col("agent") == G).sort("t")
        ot = own["t"].to_numpy()
        kinds = Counter()
        for row in spans.iter_rows(named=True):
            t0, t1 = row["t0"].timestamp() * 1e6, row["t1"].timestamp() * 1e6
            lo, hi = np.searchsorted(ot, t0, "left"), np.searchsorted(ot, t1, "right")
            kinds.update(own.slice(lo, hi - lo)["kind"].to_list())
        print("Gemini's own rows inside its runs, by kind:", kinds.most_common(8))
        spans = spans.with_columns(pl.col("text").str.contains(STAND).alias("standby"),
                                   pl.col("text").str.contains(BLOCK).alias("blocked"))
        print("run texts by words (standby = wait/monitor/silence/complete...; blocked = fail/error/unable/stuck...):")
        print(spans.group_by(["standby", "blocked"]).agg(pl.len().alias("runs"), pl.col("n").sum().alias("msgs"))
              .sort("runs", descending=True))
        fr = spans.filter(pl.col("text").str.contains(FRAME.pattern))
        print(f"run texts with frame words: {fr.height}", [(str(t)[:10], i[:8]) for t, i in zip(fr["t0"], fr["id0"])])

    if "7" in S:
        print("\n== 7 repeat after WAIT: own AGENT_TALK -> own WAIT -> own AGENT_TALK within 30 min (THOUGHT etc. skipped) ==")
        own = allrows.filter(pl.col("agent").is_not_null() & pl.col("kind").is_in(["AGENT_TALK", "WAIT"])).sort("t")
        sh = lambda c, k: pl.col(c).shift(-k).over("agent")
        own = own.with_columns(sh("kind", 1).alias("k1"), sh("kind", 2).alias("k2"), sh("text", 1).alias("t1"),
                               sh("text", 2).alias("t2"), (sh("t", 1) - pl.col("t")).alias("d1"),
                               (sh("t", 2) - pl.col("t")).alias("d2"))
        tw = own.filter((pl.col("kind") == "AGENT_TALK") & (pl.col("k1") == "WAIT") & (pl.col("k2") == "AGENT_TALK")
                        & (pl.col("d2") <= GAP)).with_columns((pl.col("text") == pl.col("t2")).alias("same"))
        tt = own.filter((pl.col("kind") == "AGENT_TALK") & (pl.col("k1") == "AGENT_TALK") & (pl.col("d1") <= GAP))
        x = (tw.group_by("agent").agg(pl.len().alias("talk_wait_talk"), pl.col("same").sum().alias("same_after_wait"))
             .join(tt.group_by("agent").agg(pl.len().alias("talk_talk"),
                                             (pl.col("text") == pl.col("t1")).sum().alias("same_direct")),
                   on="agent", how="full", coalesce=True).fill_null(0)
             .with_columns((pl.col("same_after_wait") / pl.col("talk_wait_talk")).round(3).alias("p_after_wait"),
                           (pl.col("same_direct") / pl.col("talk_talk")).round(4).alias("p_direct"))
             .sort("talk_wait_talk", descending=True))
        with pl.Config(tbl_rows=12):
            print(x.head(10))
        gdays = tw.filter(pl.col("agent") == G).select("day").unique()
        sub = tw.join(gdays, on="day")
        gm, om = sub.filter(pl.col("agent") == G), sub.filter(pl.col("agent") != G)
        print(f"same days ({gdays.height} days with a {G} talk-wait-talk): {G} {gm['same'].sum()}/{gm.height} = "
              f"{gm['same'].mean():.3f}; others {om['same'].sum()}/{om.height} = {om['same'].mean():.3f}")
        dm = (sub.with_columns((pl.col("agent") == G).alias("g")).group_by("day", maintain_order=True)
              .agg(pl.col("same").filter(pl.col("g")).sum().alias("gs"), pl.col("g").sum().alias("gn"),
                   pl.col("same").filter(~pl.col("g")).sum().alias("os"), (~pl.col("g")).sum().alias("on"))
              .sort("day").select("gs", "gn", "os", "on").to_numpy().astype(float))
        rng = np.random.default_rng(7)
        bs = dm[rng.integers(0, len(dm), size=(a.n, len(dm)))].sum(axis=1)
        diff = bs[:, 0] / bs[:, 1] - bs[:, 2] / np.maximum(bs[:, 3], 1)
        print(f"   day-block bootstrap of the difference (n={a.n}): 95% CI [{np.percentile(diff, 2.5):.3f}, "
              f"{np.percentile(diff, 97.5):.3f}], share <= 0: {(diff <= 0).mean():.4f}")
        bym = tw.filter(pl.col("agent") == G).group_by(pl.col("time").dt.strftime("%Y-%m").alias("month")).agg(
            pl.len(), pl.col("same").mean().round(3).alias("p_same")).sort("month")
        print(f"{G} by month:", list(zip(bym["month"], bym["len"], bym["p_same"])))


if __name__ == "__main__":
    main()
