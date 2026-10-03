# Population-level spread stats over the core named coinages (cap_ratio>=0.8, HR class coinage_like, >=5 agents, >=7 days, not broadcast).
import polars as pl
R = pl.read_parquet("phrase_spread.parquet")
C = R.filter(pl.col("core") & (pl.col("cap_ratio")>=0.8) & (pl.col("hr_class")=="coinage_like"))
print("core named coinages:", C.height, " goal-day bursts:", C["goal_day_burst"].sum())
# L3: survival beyond originating goal, burst vs gradual
print(C.group_by("goal_day_burst").agg(pl.len(), (pl.col("agents_after_goal_end")>=3).mean().alias("frac_3plus_agents_after_goal"), pl.col("days_used_after_goal_end").median().alias("med_days_after_goal"), pl.col("t5_h").median().alias("med_t5_h")))
# L4: adoption channels
s = C.select(*[pl.col(c).sum() for c in ["ch_room_1h","ch_heard_24h","ch_own_memory","ch_cold","n_adopters","newcomer_adopters","newcomer_fast_2h"]])
print(s)
# L1: coiner departure
hits = pl.read_parquet("chat_hits.parquet").join(pl.read_parquet("chat_index.parquet").select("i","time","kind"), on="i").filter(pl.col("kind")=="agent")
G = C.filter(pl.col("origin_gone")).select("cid","form","origin","origin_left")
h = hits.join(G, on="cid")
alive = h.filter((pl.col("time")<=pl.col("origin_left")) & (pl.col("time")>pl.col("origin_left")-pl.duration(days=30))).select("cid").unique()
after = h.filter(pl.col("time")>pl.col("origin_left")+pl.duration(days=1)).group_by("cid").agg(pl.len().alias("n_after"))
A = G.join(alive, on="cid", how="semi").join(after, on="cid", how="left").with_columns(pl.col("n_after").fill_null(0))
print("coinages alive in coiner's last 30 days:", A.height, " used again after coiner left:", (A["n_after"]>0).sum())
print(A.group_by("origin").agg(pl.len(), (pl.col("n_after")>0).sum().alias("survived")).sort("len", descending=True))
# control: coinages whose coiner stayed; pseudo-departure = each departing agent's leave date, same 30d-alive rule
stay = C.filter(~pl.col("origin_gone")).select("cid")
leaves = G.select("origin_left").unique()["origin_left"].to_list()
tot=surv=0
for L in leaves:
    hs = hits.join(stay, on="cid")
    al = hs.filter((pl.col("time")<=L) & (pl.col("time")>L-pl.timedelta(days=30) if False else pl.lit(L)-pl.duration(days=30))) if False else None
    a = hs.filter(pl.col("time").is_between(L - __import__("datetime").timedelta(days=30), L))["cid"].unique()
    s2 = hs.filter((pl.col("time")>L + __import__("datetime").timedelta(days=1)) & pl.col("cid").is_in(a.to_list()))["cid"].n_unique()
    tot += len(a); surv += s2
print("control (coiner stayed), same dates:", tot, "alive;", surv, "used again after the date")
