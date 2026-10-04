# Memory channel: chat -> own memory notes -> later "cold" chat use (no one else used P in the prior 24h).
import polars as pl
from phrases import COINAGES
pl.Config.set_tbl_rows(80); pl.Config.set_tbl_width_chars(220)
P = dict(COINAGES); P.update({"live and verified": r"live and verified", "exactly right": r"exactly right", "standing by": r"standing by",
          "absolutely right": r"absolutely right", "heads up": r"\bheads[ -]up\b"})
COLD = pl.duration(hours=24)
def ds_split(df):
    DS = pl.col("agent")=="DeepSeek-V3.2"
    return df.with_columns(pl.when(DS & (pl.col("time")<pl.datetime(2026,4,22))).then(pl.lit("DeepSeek-V3.2"))
        .when(DS & (pl.col("time")>=pl.datetime(2026,4,25))).then(pl.lit("DeepSeek-V3.2>V4Flash"))
        .when(DS).then(pl.lit("DeepSeek-V3.2 (swap gap)")).otherwise(pl.col("agent")).alias("agent"))
union = "(?i)(" + "|".join(P.values()) + ")"
mem = ds_split(pl.scan_parquet("../../village_raw.parquet").filter(pl.col("kind")=="memory")
       .select("time","agent","text","dropped").filter(pl.col("text").str.contains(union) | pl.col("dropped").fill_null("").str.contains(union)).collect())
chat = ds_split(pl.read_parquet("../../chat_raw.parquet", columns=["time","kind","agent","text"]).filter(pl.col("text").str.contains(union)))
print("memory rows touching phrases:", mem.height)
rows=[]; ex=[]
for name, rx in P.items():
    r = "(?i)"+rx
    m = mem.with_columns(pl.col("text").str.count_matches(r).alias("add"), pl.col("dropped").fill_null("").str.count_matches(r).alias("drop")).filter((pl.col("add")+pl.col("drop"))>0)
    m = m.sort("time").with_columns((pl.col("add")-pl.col("drop")).cum_sum().over("agent").alias("net"))
    c = chat.filter(pl.col("text").str.contains(r)).sort("time")
    ag = c.filter(pl.col("kind")=="agent")
    for (A,), ca in ag.group_by("agent"):
        others = c.filter(~((pl.col("agent")==A)&(pl.col("kind")=="agent"))).select(pl.col("time").alias("t_o")).sort("t_o")
        ca = ca.sort("time").join_asof(others, left_on="time", right_on="t_o", strategy="backward")
        mA = m.filter(pl.col("agent")==A).select(pl.col("time").alias("t_m"), "net", "add").sort("t_m")
        ca = ca.join_asof(mA, left_on="time", right_on="t_m", strategy="backward")
        ca = ca.with_columns((pl.col("t_o").is_null() | ((pl.col("time")-pl.col("t_o"))>COLD)).alias("cold"),
                             (pl.col("net").fill_null(0)>0).alias("in_mem"))
        first_mem = mA.filter(pl.col("add")>0)["t_m"].min() if mA.height else None
        first_chat = ca["time"].min(); first_other = others["t_o"].min() if others.height else None
        rows.append(dict(phrase=name, agent=A, uses=ca.height, cold=int(ca["cold"].sum()), cold_in_mem=int((ca["cold"]&ca["in_mem"]).sum()),
             warm_in_mem=int((~ca["cold"]&ca["in_mem"]).sum()), mem_adds=int(mA["add"].sum()) if mA.height else 0,
             mem_before_first_chat=(first_mem is not None and first_mem < first_chat),
             heard_before_first_chat=(first_other is not None and first_other < first_chat)))
        ex.append(ca.filter(pl.col("cold")).with_columns(pl.lit(name).alias("phrase")).select("phrase","agent","time","in_mem","t_o","text"))
R = pl.DataFrame(rows)
R.write_csv("memory_channel_by_agent.csv")
coin = set(COINAGES)
S = (R.with_columns(pl.col("phrase").is_in(list(coin)).alias("coinage")).group_by("phrase","coinage")
     .agg(pl.len().alias("users"), pl.col("uses").sum(), pl.col("cold").sum(), pl.col("cold_in_mem").sum(),
          (pl.col("mem_adds")>0).sum().alias("users_with_mem_notes"), pl.col("mem_before_first_chat").sum().alias("mem_first"),
          (pl.col("mem_before_first_chat") & ~pl.col("heard_before_first_chat")).sum().alias("mem_first_unheard"))
     .with_columns((pl.col("cold")/pl.col("uses")).round(3).alias("cold_share"), (pl.col("cold_in_mem")/pl.col("cold")).round(2).alias("cold_backed_by_memory"))
     .sort("coinage","cold_backed_by_memory", descending=True))
print(S); S.write_csv("memory_channel_summary.csv")
for k, d in R.with_columns(pl.col("phrase").is_in(list(coin)).alias("coinage")).group_by("coinage"):
    print("coinage" if k[0] else "tic", "uses", d["uses"].sum(), "cold", d["cold"].sum(), "cold&in_mem", d["cold_in_mem"].sum(), "users", d.height, "users w/ memory notes", (d["mem_adds"]>0).sum())
pl.concat(ex).write_parquet("cold_uses.parquet")
