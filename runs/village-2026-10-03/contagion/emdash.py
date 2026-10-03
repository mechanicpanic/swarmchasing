# Spaced em-dash lead (coordinator): separate exposure channels for older agents, Jan 15 - Apr 21 2026.
# Per message of target A: (1) A's latest inbound @-message in prior 2h: from human/nudger with " — ", from a 4.6 agent with " — ",
# from anyone else with " — ", inbound without " — ", or none.  (2) room: did a 4.6 agent post " — " in the room in prior 60 min.
# Outcome: A's message contains " — ". MH rate ratio vs "inbound without em-dash", strata = agent x ISO week x room-4.6-exposure.
import polars as pl, numpy as np
pl.Config.set_tbl_rows(80); pl.Config.set_tbl_width_chars(220)
chat = (pl.read_parquet("../../chat_raw.parquet", columns=["time","kind","agent","room","text"])
        .filter((pl.col("time")>=pl.datetime(2026,1,15)) & (pl.col("time")<pl.datetime(2026,4,21))).sort("time")
        .with_columns(pl.col("text").str.contains(" — ", literal=True).alias("ed")))
NEW = ["Claude Opus 4.6","Claude Sonnet 4.6"]
TARGETS = ["Claude Opus 4.5","DeepSeek-V3.2","GPT-5.1","GPT-5.2","Gemini 3 Pro","Gemini 2.5 Pro","Claude Haiku 4.5","Claude Sonnet 4.5","Opus 4.5 (Claude Code)","Claude 3.7 Sonnet"]
def src_cat(kind, agent, ed):
    return (pl.when(~ed).then(pl.lit("inbound, no em-dash"))
            .when(kind=="user").then(pl.lit("human/nudger + em-dash"))
            .when(agent.is_in(NEW)).then(pl.lit("4.6 agent + em-dash"))
            .otherwise(pl.lit("other agent + em-dash")))
room46 = chat.filter(pl.col("agent").is_in(NEW) & pl.col("ed")).select(pl.col("time").alias("t46"), "room").sort("t46")
out=[]
for A in TARGETS:
    mine = chat.filter((pl.col("agent")==A)&(pl.col("kind")=="agent")).select("time","room","ed")
    if mine.height < 50: continue
    inbound = chat.filter(pl.col("text").str.contains("@"+A, literal=True) & ~((pl.col("agent")==A)&(pl.col("kind")=="agent"))) \
                  .select(pl.col("time").alias("t_in"), src_cat(pl.col("kind"), pl.col("agent"), pl.col("ed")).alias("cat")).sort("t_in")
    m = mine.sort("time").join_asof(inbound, left_on="time", right_on="t_in", strategy="backward") \
            .join_asof(room46, left_on="time", right_on="t46", by="room", strategy="backward")
    m = m.with_columns(pl.when(pl.col("t_in").is_null() | ((pl.col("time")-pl.col("t_in"))>pl.duration(hours=2))).then(pl.lit("no inbound @ in 2h")).otherwise(pl.col("cat")).alias("cat"),
                       (pl.col("t46").is_not_null() & ((pl.col("time")-pl.col("t46"))<=pl.duration(minutes=60))).alias("room46"),
                       pl.col("time").dt.strftime("%G-W%V").alias("wk"), pl.lit(A).alias("agent"))
    out.append(m.select("agent","wk","room46","cat","ed"))
M = pl.concat(out)
print(M.group_by("cat").agg(pl.len(), pl.col("ed").mean().round(3)).sort("cat"))
def mh(df, col, val, ref):
    d = df.filter(pl.col(col).is_in([val, ref]))
    t = d.group_by("agent","wk","room46" if col!="room46" else "cat").agg(
        pl.col("ed").filter(pl.col(col)==val).sum().alias("a"), (pl.col(col)==val).sum().alias("n1"),
        pl.col("ed").filter(pl.col(col)==ref).sum().alias("b"), (pl.col(col)==ref).sum().alias("n0")).filter((pl.col("n1")>0)&(pl.col("n0")>0)).with_columns((pl.col("n1")+pl.col("n0")).alias("N"))
    num=(t["a"]*t["n0"]/t["N"]).sum(); den=(t["b"]*t["n1"]/t["N"]).sum()
    v=((t["a"]+t["b"])*t["n1"]*t["n0"]/t["N"]**2).sum(); se=np.sqrt(v/(num*den)) if num>0 and den>0 else np.nan
    rr=num/den if den>0 else np.nan
    return dict(contrast=f"{val} vs {ref}", RR=round(rr,2), lo=round(rr*np.exp(-1.96*se),2), hi=round(rr*np.exp(1.96*se),2), n_exposed=int(t["n1"].sum()))
rows=[mh(M,"cat",c,"inbound, no em-dash") for c in ["human/nudger + em-dash","4.6 agent + em-dash","other agent + em-dash"]]
rows.append(mh(M.with_columns(pl.col("room46").cast(pl.Utf8)),"room46","true","false"))
R=pl.DataFrame(rows); print(R); R.write_csv("emdash_channels.csv")
# per agent
pa=[]
for (A,),d in M.group_by("agent"):
    for c in ["human/nudger + em-dash","4.6 agent + em-dash"]:
        r=mh(d,"cat",c,"inbound, no em-dash"); r["agent"]=A; pa.append(r)
print(pl.DataFrame(pa).sort("agent"))
