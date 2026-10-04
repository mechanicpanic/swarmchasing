# Score a curated list of tics / preoccupations (regex on raw text) per agent,
# in chat and in THOUGHT rows. Writes candidates.csv (hand-off for the contagion
# thread) and cand_rates_long.parquet (agent x candidate x src).
# Rate = messages containing the pattern per 1,000 messages (dedup same-agent
# identical texts). obs/exp = agent's count / count expected if the agent used
# it at the same-week rate of all *other* agents (time-matched background).
import polars as pl
from cand_list import CANDS

DIR = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/tics/"
CORP = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/"
HIDE = {"GPT-5.6 Terra", "GPT-5.6 Luna"}  # asked not to be named: aggregate only


DS_PRE, DS_POST = "DeepSeek-V3.2 (pre-swap)", "DeepSeek (post-swap, likely V4-Flash)"


def split_deepseek(d):
    """The 'DeepSeek-V3.2' agent's endpoint was rerouted to V4-Flash on 2026-04-24
    (models-table thread). Treat pre-2026-04-22 and post-2026-04-24 as two models;
    drop the gap days."""
    ds = pl.col("agent") == "DeepSeek-V3.2"
    d = d.filter(~(ds & pl.col("time").is_between(pl.datetime(2026, 4, 22), pl.datetime(2026, 4, 24))))
    return d.with_columns(pl.when(ds & (pl.col("time") < pl.datetime(2026, 4, 22))).then(pl.lit(DS_PRE))
                          .when(ds).then(pl.lit(DS_POST)).otherwise(pl.col("agent")).alias("agent"))


def docs(src):
    if src == "chat":
        d = (pl.read_parquet(CORP + "chat_raw.parquet", columns=["id", "time", "kind", "agent", "text"])
             .filter(pl.col("kind") == "agent").drop("kind"))
    else:
        d = (pl.scan_parquet(CORP + "../village_embeddings_2026-09-29/3_village_full_with_text.parquet")
             .filter(pl.col("kind") == "THOUGHT").select("id", "time", "agent", "text").collect()
             .with_columns(pl.col("time").dt.replace_time_zone(None)))
    d = split_deepseek(d)
    return (d.filter(pl.col("text").is_not_null()).sort("time")
            .unique(["agent", "text"], keep="first", maintain_order=True)
            .with_columns(pl.col("time").dt.truncate("1w").alias("week")))


def score(d, src):
    flags = d.select("id", "time", "week", "agent",
                     *[pl.col("text").str.contains(rx).alias(name) for name, rx, kind in CANDS])
    names = [c[0] for c in CANDS]
    long = flags.unpivot(index=["id", "time", "week", "agent"], on=names, variable_name="cand", value_name="hit")
    aw = long.group_by("cand", "agent", "week").agg(pl.len().alias("n"), pl.col("hit").sum().alias("y"))
    wk = aw.group_by("cand", "week").agg(pl.col("n").sum().alias("N"), pl.col("y").sum().alias("Y"))
    aw = aw.join(wk, on=["cand", "week"]).with_columns(
        exp=pl.when(pl.col("N") > pl.col("n")).then(pl.col("n") * (pl.col("Y") - pl.col("y")) / (pl.col("N") - pl.col("n"))).otherwise(None))
    per = aw.group_by("cand", "agent").agg(pl.col("n").sum(), pl.col("y").sum(), pl.col("exp").sum())
    per = per.with_columns(rate_1k=1000 * pl.col("y") / pl.col("n"),
                           obs_exp=(pl.col("y") + 0.5) / (pl.col("exp") + 0.5), src=pl.lit(src))
    first = (long.filter("hit").sort("time").group_by("cand")
             .agg(pl.col("time").first().alias("first_time"), pl.col("agent").first().alias("first_agent"),
                  pl.col("agent").n_unique().alias("n_agents"), pl.len().alias("total")))
    return per, first


rows, per_all = [], []
pc, fc = score(docs("chat"), "chat")
pt, ft = score(docs("thought"), "thought")
per_all = pl.concat([pc, pt])
per_all.write_parquet(DIR + "cand_rates_long.parquet")

kinds = {n: k for n, rx, k in CANDS}
rxs = {n: rx for n, rx, k in CANDS}
for name, rx, kind in CANDS:
    p = pc.filter((pl.col("cand") == name) & (pl.col("n") >= 100) & ~pl.col("agent").is_in(HIDE))
    top = p.filter(pl.col("y") >= 5).sort("rate_1k", descending=True).head(5)
    th = pt.filter((pl.col("cand") == name) & (pl.col("n") >= 100) & ~pl.col("agent").is_in(HIDE)).sort("rate_1k", descending=True).head(3)
    f = fc.filter(pl.col("cand") == name)
    fth = ft.filter(pl.col("cand") == name)
    vill = pc.filter(pl.col("cand") == name)
    rows.append(dict(
        name=name, kind=kind, regex=rx,
        chat_total_msgs=int(f["total"][0]) if f.height else 0,
        chat_n_agents=int(f["n_agents"][0]) if f.height else 0,
        village_rate_1k=round(1000 * vill["y"].sum() / vill["n"].sum(), 2),
        top_agents_chat="; ".join(f"{a} {r:.1f} (x{o:.1f})" for a, r, o in zip(top["agent"], top["rate_1k"], top["obs_exp"])),
        top_agents_thought="; ".join(f"{a} {r:.1f}" for a, r in zip(th["agent"], th["rate_1k"])),
        first_use_chat=str(f["first_time"][0])[:16] if f.height else "",
        first_agent_chat=(f["first_agent"][0] if f["first_agent"][0] not in HIDE else "GPT-5.6 (2026H2 OpenAI)") if f.height else "",
        thought_total=int(fth["total"][0]) if fth.height else 0,
    ))
out = pl.DataFrame(rows)
out.write_csv(DIR + "candidates.csv")
pl.Config.set_tbl_rows(80); pl.Config.set_fmt_str_lengths(120); pl.Config.set_tbl_width_chars(300)
print(out.select("name", "kind", "chat_total_msgs", "chat_n_agents", "top_agents_chat", "first_agent_chat", "first_use_chat"))
