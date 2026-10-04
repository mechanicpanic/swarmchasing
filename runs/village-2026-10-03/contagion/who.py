# (a) same-lab vs other-lab exposure (within-agent MH lift, clean-day spec)
# (b) susceptibility: per agent, MH lift pooled over phrases; and share of its adoptions that came right after exposure
# (c) spreaders: whose use most often immediately precedes another agent's FIRST use (candidate source), per 1k of own uses
import polars as pl
from lift2 import mh_table, mh
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_width_chars(220)
S = pl.concat([pl.read_parquet("strata.parquet"), pl.read_parquet("strata_tics.parquet").filter(pl.col("pkind")!="tic")])  # own tics + tics-thread preoccupations
S = pl.concat([pl.read_parquet("strata.parquet"), pl.read_parquet("strata_tics.parquet").with_columns(pl.col("phrase")+" [t]")])
C = S.filter(~pl.col("selfrec") & ~pl.col("humrec") & ~pl.col("exp_hum"))
K = ["phrase","agent","day","selfrec","humrec","act"]
rows=[]
for kind in ["coinage","tic","preoccupation","null"]:
    d = C.filter(pl.col("pkind")==kind)
    # same-lab-only exposure vs unexposed ; other-lab-only exposure vs unexposed
    same = d.filter(~(pl.col("exp") & ~pl.col("exp_same")))   # keep unexposed + exposed-by-same-lab-only
    same = same.filter(~(pl.col("exp_same") & pl.col("exp_diff")))
    diff = d.filter(~(pl.col("exp") & ~pl.col("exp_diff"))).filter(~(pl.col("exp_same") & pl.col("exp_diff")))
    for lab, dd in [("same-lab only", same), ("other-lab only", diff)]:
        t = mh_table(dd, "exp", K); rr,lo,hi = mh(t)
        rows.append(dict(kind=kind, exposure=lab, RR=round(rr,2), lo=round(lo,2), hi=round(hi,2), exp_hits=int(t["a"].sum())))
    t = mh_table(d, "exp_at", K); rr,lo,hi = mh(t)
    rows.append(dict(kind=kind, exposure="@-mentioned A (vs not)", RR=round(rr,2), lo=round(lo,2), hi=round(hi,2), exp_hits=int(t["a"].sum())))
lab = pl.DataFrame(rows); print(lab); lab.write_csv("lift_by_lab_and_mention.csv")

# (b) susceptibility per agent (tics+preoccupations+coinages, clean spec)
d = C.filter(pl.col("pkind")!="null")
rows=[]
for (A,), dd in d.group_by("agent"):
    t = mh_table(dd, "exp", K)
    if t["a"].sum() < 15: continue
    rr,lo,hi = mh(t); rows.append(dict(agent=A, RR=round(rr,2), lo=round(lo,2), hi=round(hi,2), exp_hits=int(t["a"].sum())))
sus = pl.DataFrame(rows).sort("RR", descending=True); sus.write_csv("susceptibility_by_agent.csv")
print(sus.filter(~pl.col("agent").str.contains("GPT-5.6 (Luna|Terra)")))

# (c) spreaders from first-use attribution (tics + coinages + preoccupations; distinct phrase regexes only)
a = pl.read_parquet("adoptions.parquet").filter(pl.col("exposed_1h_same_room") & pl.col("src").is_not_null())
chat = pl.read_parquet("../../chat_raw.parquet", columns=["agent","kind"]).filter(pl.col("kind")=="agent").group_by("agent").len()
sp = (a.group_by("src").agg(pl.len().alias("seeded_adoptions"), pl.col("agent").n_unique().alias("distinct_adopters"),
        (pl.col("pkind")=="coinage").sum().alias("coinage_seeds"))
      .join(chat.rename({"agent":"src","len":"msgs"}), on="src", how="left")
      .with_columns((1000*pl.col("seeded_adoptions")/pl.col("msgs")).round(2).alias("per_1k_msgs")).sort("seeded_adoptions", descending=True))
sp.write_csv("spreaders.csv")
print(sp.filter(~pl.col("src").str.contains("GPT-5.6 (Luna|Terra)")).head(20))
# same-lab share of attributed adoptions vs share expected if source were a random speaker in the room
lab_of = pl.read_parquet("../../chat_raw.parquet", columns=["agent","lab"]).unique("agent")
aa = a.join(lab_of.rename({"agent":"src","lab":"src_lab"}), on="src", how="left")
print("attributed adoptions with same-lab source:", (aa["src_lab"]==aa["lab"]).mean(), "n", aa.height)
