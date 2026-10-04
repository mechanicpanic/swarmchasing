# Exposure -> use, within agent, with controls. For phrase P and target agent A, each message m of A gets:
#   exp      : someone else (agent or human) used P in the same room in the 60 min before m
#   selfrec  : A itself used P in the same room in the prior 60 min
#   humrec   : ANY human message in the room in the prior 60 min (common-stimulus control)
#   act      : bin of # other messages in room in prior 60 min (busy-room control)
#   exp_same / exp_diff / exp_hum / exp_at : exposure from same-lab agent / other-lab agent / human / message @-mentioning A
# Output: strata counts by (agent, day, selfrec, humrec, act, exposure flags) and per-(phrase, agent) first-use rows.
import polars as pl, numpy as np, sys, csv
from phrases import COINAGES, TICS, NULLS
W = pl.duration(minutes=60); WNS = np.int64(60*60*1_000_000)
chat = (pl.read_parquet("../../chat_raw.parquet", columns=["id","time","kind","agent","room","lab","cohort","text"])
        .sort("time").with_row_index("i"))
# Coordinator: "DeepSeek-V3.2" endpoint was rerouted to V4-Flash on 2026-04-24 -> split; gap days 04-22..04-24 kept as source only.
DS = pl.col("agent")=="DeepSeek-V3.2"
chat = chat.with_columns(pl.when(DS & (pl.col("time")<pl.datetime(2026,4,22))).then(pl.lit("DeepSeek-V3.2"))
    .when(DS & (pl.col("time")>=pl.datetime(2026,4,25))).then(pl.lit("DeepSeek-V3.2>V4Flash"))
    .when(DS).then(pl.lit("DeepSeek-V3.2 (swap gap)")).otherwise(pl.col("agent")).alias("agent"))
agents = (chat.filter(pl.col("kind")=="agent").group_by("agent").agg(pl.len().alias("n"), pl.col("lab").first().alias("alab"),
          pl.col("cohort").first().alias("acohort"), pl.col("time").min().alias("arrive")).filter((pl.col("n")>=100)&(pl.col("agent")!="DeepSeek-V3.2 (swap gap)")))
mode = sys.argv[1] if len(sys.argv)>1 else "own"
if mode == "own":
    ALLP = {**{k:("coinage",v) for k,v in COINAGES.items()}, **{k:("tic",v) for k,v in TICS.items()}, **{k:("null",v) for k,v in NULLS.items()}}
else:  # tics thread candidates
    ALLP = {r["name"]:(r["kind"], r["regex"]) for r in csv.DictReader(open("../tics/candidates.csv"))}

def flag(rx):
    if len(rx)==1: return pl.col("text").str.contains(rx, literal=True)
    return pl.col("text").str.contains(rx if rx.startswith("(?") else "(?i)"+rx)

# precompute per-agent context that does not depend on phrase
hum = chat.filter(pl.col("kind")=="user").select(pl.col("time").alias("t_h"), "room").sort("t_h")
room_times = {r: g["time"].cast(pl.Int64).to_numpy() for (r,), g in chat.group_by("room")}
ctx = {}
for a in agents.iter_rows(named=True):
    A = a["agent"]
    mine = chat.filter((pl.col("agent")==A)&(pl.col("kind")=="agent")).select("i","time","room","text").sort("time")
    mine = mine.join_asof(hum, left_on="time", right_on="t_h", by="room", strategy="backward", allow_exact_matches=False)
    t = mine["time"].cast(pl.Int64).to_numpy(); rooms = mine["room"].to_list()
    act = np.zeros(len(t), dtype=np.int64)
    own_by_room = {}
    for r in set(rooms):
        idx = np.array([j for j,x in enumerate(rooms) if x==r]); rt = room_times[r]; ot = t[idx]
        n_all = np.searchsorted(rt, ot, "left") - np.searchsorted(rt, ot-WNS, "left")
        n_own = np.searchsorted(ot, ot, "left") - np.searchsorted(ot, ot-WNS, "left")
        act[idx] = n_all - n_own
    mine = mine.with_columns(pl.Series("act_n", act),
        (pl.col("t_h").is_not_null() & ((pl.col("time")-pl.col("t_h"))<=W)).alias("humrec"),
        pl.col("time").dt.date().alias("day"), pl.col("time").dt.hour().alias("hour")).with_columns(
        pl.col("act_n").cut([2,10,30], labels=["0-2","3-10","11-30","31+"]).cast(pl.Utf8).alias("act"))
    ctx[A] = mine.drop("t_h")

strata_rows, first_rows = [], []
for name,(kind,rx) in ALLP.items():
    hitcol = flag(rx).fill_null(False)
    hits = chat.filter(hitcol).select("time","room","agent","kind","lab","text")
    if hits.height < 10: print("skip", name, hits.height); continue
    gfirst = hits["time"].min(); origin = hits.sort("time")["agent"][0]
    for a in agents.iter_rows(named=True):
        A = a["agent"]
        m = ctx[A].with_columns(hitcol.alias("hit"))
        other = hits.filter(~((pl.col("agent")==A)&(pl.col("kind")=="agent")))
        oth = other.select(pl.col("time").alias("t_o"), "room", pl.col("agent").alias("src")).sort("t_o")
        m = m.join_asof(oth, left_on="time", right_on="t_o", by="room", strategy="backward", allow_exact_matches=False)
        for tag, f in [("t_same", (pl.col("kind")=="agent")&(pl.col("lab")==a["alab"])),
                       ("t_diff", (pl.col("kind")=="agent")&(pl.col("lab")!=a["alab"])),
                       ("t_hum", pl.col("kind")=="user"),
                       ("t_at", pl.col("text").str.contains("@"+A, literal=True))]:
            m = m.join_asof(other.filter(f).select(pl.col("time").alias(tag), "room").sort(tag), left_on="time", right_on=tag, by="room", strategy="backward", allow_exact_matches=False)
        m = m.join_asof(m.filter("hit").select(pl.col("time").alias("t_self"), "room").sort("t_self"), left_on="time", right_on="t_self", by="room", strategy="backward", allow_exact_matches=False)
        m = m.join_asof(other.select(pl.col("time").alias("t_ever")).sort("t_ever"), left_on="time", right_on="t_ever", strategy="backward", allow_exact_matches=False)
        win = lambda col: (pl.col(col).is_not_null() & ((pl.col("time")-pl.col(col)) <= W))
        m = m.with_columns(win("t_o").alias("exp"), win("t_same").alias("exp_same"), win("t_diff").alias("exp_diff"),
                           win("t_hum").alias("exp_hum"), win("t_at").alias("exp_at"), win("t_self").alias("selfrec"))
        strata_rows.append(m.group_by("day","hour","selfrec","humrec","act","exp","exp_same","exp_diff","exp_hum","exp_at")
                .agg(pl.len().alias("n"), pl.col("hit").sum().alias("k"))
                .with_columns(pl.lit(name).alias("phrase"), pl.lit(kind).alias("pkind"), pl.lit(A).alias("agent")))
        fu = m.filter("hit").head(1)
        upto = fu["time"][0] if fu.height else m["time"].max()
        pre = m.filter((pl.col("time")>gfirst)&(pl.col("time")<upto))
        base = dict(phrase=name, pkind=kind, agent=A, lab=a["alab"], cohort=a["acohort"], arrive=a["arrive"], n_msgs=m.height,
                    n_hits=int(m["hit"].sum()), global_first=gfirst, origin=origin, pre_msgs=pre.height,
                    pre_exp_rate=(float(pre["exp"].mean()) if pre.height else None), pre_exposed_msgs=int(pre["exp"].sum()) if pre.height else 0)
        if fu.height:
            r = fu.row(0, named=True); prior = other.filter(pl.col("time") < r["time"])
            base.update(first_use=r["time"], msgs_before_first=int((m["time"]<r["time"]).sum()), prior_uses_by_others=prior.height,
                prior_uses_since_arrival=prior.filter(pl.col("time")>=a["arrive"]).height,
                hours_since_last_other=(None if r["t_ever"] is None else (r["time"]-r["t_ever"]).total_seconds()/3600),
                exposed_1h_same_room=bool(r["exp"]), at_exposed=bool(r["exp_at"]), src=(r["src"] if r["exp"] else None),
                humrec_at_first=bool(r["humrec"]), hours_since_arrival=(r["time"]-a["arrive"]).total_seconds()/3600)
        first_rows.append(base)
    print(name, kind, hits.height, flush=True)
suffix = "" if mode=="own" else "_tics"
pl.concat(strata_rows).write_parquet(f"strata{suffix}.parquet")
pl.DataFrame(first_rows, infer_schema_length=None).write_parquet(f"first_use{suffix}.parquet")
