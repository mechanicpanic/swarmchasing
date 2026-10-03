# Exposure -> use, within agent. For each phrase P and each target agent A:
# every message m of A is "exposed" if someone else (agent or human) used P in the
# same room in the 60 min before m. Strata = (agent, day, A itself used P in prior 60 min).
# Mantel-Haenszel rate ratio over strata = within-agent-day lift.
import polars as pl, sys
from phrases import COINAGES, TICS, NULLS
W = pl.duration(minutes=60)
chat = (pl.read_parquet("../../chat_raw.parquet", columns=["id","time","kind","agent","room","lab","cohort","text"])
        .sort("time").with_row_index("i"))
agents = (chat.filter(pl.col("kind")=="agent").group_by("agent").agg(pl.len().alias("n"), pl.col("lab").first().alias("alab"),
          pl.col("cohort").first().alias("acohort"), pl.col("time").min().alias("arrive")).filter(pl.col("n")>=100))
ALLP = {**{k:("coinage",v) for k,v in COINAGES.items()}, **{k:("tic",v) for k,v in TICS.items()}, **{k:("null",v) for k,v in NULLS.items()}}
if len(sys.argv)>1:
    import csv
    for r in csv.DictReader(open(sys.argv[1])): ALLP[r["phrase"]]=(r.get("kind","tics_thread"), r["regex"])

def flag(regex):
    if len(regex) == 1:
        return pl.col("text").str.contains(regex, literal=True)
    return pl.col("text").str.contains("(?i)"+regex)

strata_rows, first_rows = [], []
for name,(kind,rx) in ALLP.items():
    c = chat.with_columns(flag(rx).fill_null(False).alias("hit"))
    hits = c.filter("hit").select("time","room","agent","kind","lab","text")
    if hits.height < 10: print("skip", name, hits.height); continue
    for a in agents.iter_rows(named=True):
        A = a["agent"]
        mine = c.filter((pl.col("agent")==A)&(pl.col("kind")=="agent")).select("i","time","room","hit")
        other = hits.filter(~((pl.col("agent")==A)&(pl.col("kind")=="agent")))
        def last(src, tag):
            s = src.select(pl.col("time").alias(tag), "room").sort(tag)
            return s
        m = mine.sort("time")
        # any other speaker, same room
        m = m.join_asof(other.select(pl.col("time").alias("t_o"), "room").sort("t_o"), left_on="time", right_on="t_o", by="room", strategy="backward", allow_exact_matches=False)
        # other AGENT same lab / other lab / human
        for tag, f in [("t_same", (pl.col("kind")=="agent")&(pl.col("lab")==a["alab"])),
                       ("t_diff", (pl.col("kind")=="agent")&(pl.col("lab")!=a["alab"])),
                       ("t_hum", pl.col("kind")=="user"),
                       ("t_at", pl.col("text").str.contains("@"+A, literal=True))]:
            m = m.join_asof(other.filter(f).select(pl.col("time").alias(tag), "room").sort(tag), left_on="time", right_on=tag, by="room", strategy="backward", allow_exact_matches=False)
        # self recent
        m = m.join_asof(mine.filter("hit").select(pl.col("time").alias("t_self"), "room").sort("t_self"), left_on="time", right_on="t_self", by="room", strategy="backward", allow_exact_matches=False)
        # ever heard before (any room, any time before)
        m = m.join_asof(other.select(pl.col("time").alias("t_ever")).sort("t_ever"), left_on="time", right_on="t_ever", strategy="backward", allow_exact_matches=False)
        win = lambda col: (pl.col(col).is_not_null() & ((pl.col("time")-pl.col(col)) <= W))
        m = m.with_columns(win("t_o").alias("exp"), win("t_same").alias("exp_same"), win("t_diff").alias("exp_diff"),
                           win("t_hum").alias("exp_hum"), win("t_at").alias("exp_at"), win("t_self").alias("selfrec"),
                           pl.col("time").dt.date().alias("day"))
        st = (m.group_by("day","selfrec","exp","exp_same","exp_diff","exp_hum","exp_at")
                .agg(pl.len().alias("n"), pl.col("hit").sum().alias("k"))
                .with_columns(pl.lit(name).alias("phrase"), pl.lit(kind).alias("pkind"), pl.lit(A).alias("agent")))
        strata_rows.append(st)
        # first use
        gfirst = hits["time"].min()
        fu = m.filter("hit").head(1)
        upto = fu["time"][0] if fu.height else m["time"].max()
        pre = m.filter((pl.col("time")>gfirst)&(pl.col("time")<upto))
        pre_stats = dict(pre_msgs=pre.height, pre_exp_rate=(float(pre["exp"].mean()) if pre.height else None),
                         pre_exposed_msgs=int(pre["exp"].sum()) if pre.height else 0, global_first=gfirst,
                         origin=hits.sort("time")["agent"][0])
        if fu.height:
            r = fu.row(0, named=True)
            prior_global = other.filter(pl.col("time") < r["time"])
            first_rows.append(dict(phrase=name, pkind=kind, agent=A, lab=a["alab"], cohort=a["acohort"], arrive=a["arrive"], first_use=r["time"],
                n_msgs=m.height, n_hits=int(m["hit"].sum()),
                msgs_before_first=int((m["time"]<r["time"]).sum()),
                prior_uses_by_others=prior_global.height,
                prior_uses_since_arrival=prior_global.filter(pl.col("time")>=a["arrive"]).height,
                hours_since_last_other=(None if r["t_ever"] is None else (r["time"]-r["t_ever"]).total_seconds()/3600),
                exposed_1h_same_room=bool(r["exp"]), at_exposed=bool(r["exp_at"]),
                hours_since_arrival=(r["time"]-a["arrive"]).total_seconds()/3600, **pre_stats))
        else:
            first_rows.append(dict(phrase=name, pkind=kind, agent=A, lab=a["alab"], cohort=a["acohort"], arrive=a["arrive"], first_use=None, n_msgs=m.height, n_hits=0, **pre_stats))
    print(name, kind, hits.height, flush=True)
out = sys.argv[2] if len(sys.argv)>2 else ""
pl.concat(strata_rows).write_parquet(f"strata{out}.parquet")
pl.DataFrame(first_rows, infer_schema_length=None).write_parquet(f"first_use{out}.parquet")
