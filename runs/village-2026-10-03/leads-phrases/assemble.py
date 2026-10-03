# Stage 5: filters (human names, broadcast), classification, mutations -> phrase_spread.parquet
import polars as pl, json, re
from wordfreq import zipf_frequency as Z
from rapidfuzz import fuzz
R = pl.read_parquet("metrics_raw.parquet")
hn = json.load(open("human_names.json"))
htoks = {t for n in hn for t in re.findall(r"[a-z]+", n.lower()) if len(t)>=3}
htoks = {t for t in htoks if Z(t,"en") < 4.5}
R = R.with_columns(pl.col("key").map_elements(lambda k: any(w.rstrip("'s").rstrip("'") in htoks or w in htoks for w in k.split()), return_dtype=pl.Boolean).alias("has_human_name_token"))
R = R.with_columns(
    (pl.col("in_goal_text") | pl.col("human_born")).alias("broadcast"),
    ((pl.col("h_after_goal_start")<48) & (pl.col("t4_h")<24)).fill_null(False).alias("goal_day_burst"),
    pl.when(pl.col("n_adopters")<3).then(pl.lit("too_few_adopters"))
      .when(pl.col("HR_cc")>=20).then(pl.lit("coinage_like"))
      .when(pl.col("HR_cc")>=5).then(pl.lit("mixed"))
      .otherwise(pl.lit("tic_or_plain")).alias("hr_class"))
# mutations: variants in the tics thread's n-gram vocab (df>=15) sharing the key's rarest token, fuzzy-similar
voc = pl.read_parquet("../tics/ng_chat_vocab.parquet").filter(~pl.col("g").str.contains("agentx|urlx"))
vg = voc["g"].to_list()
by_tok = {}
for g in vg:
    for t in set(g.split()): by_tok.setdefault(t, []).append(g)
def variants(k):
    ws = k.split(); rare = min(ws, key=lambda w: Z(w,"en"))
    out = []
    for g in by_tok.get(rare, []):
        if g == k or k in g: continue          # skip superstrings (context, not mutation)
        if g in k: continue
        s = fuzz.ratio(g, k)
        if s >= 75: out.append((s, g))
    return [g for s,g in sorted(out, reverse=True)[:6]]
focus = R.filter(pl.col("hr_class")!="too_few_adopters")
mut = {k: variants(k) for k in focus["key"].to_list()}
R = R.with_columns(pl.col("key").map_elements(lambda k: mut.get(k, []), return_dtype=pl.List(pl.Utf8)).alias("variants"))
R = R.with_columns(pl.col("variants").list.len().alias("n_variants"))
R = R.with_columns((~pl.col("broadcast") & ~pl.col("has_human_name_token") & (pl.col("n_agents")>=4)).alias("candidate"))
R.write_parquet("phrase_spread.parquet")
C = R.filter("candidate")
print(R.height, C.height); print(C.group_by("hr_class").len())
print(C.filter(pl.col("hr_class")=="coinage_like").height, "coinage-like; of which goal-day bursts:", C.filter((pl.col("hr_class")=="coinage_like") & pl.col("goal_day_burst")).height)
R = pl.read_parquet("phrase_spread.parquet")
R = R.with_columns((pl.col("HR_cc")*(-1.96*((1/(pl.col("adopt_exp")+0.5))+(1/(pl.col("adopt_unexp")+0.5))).sqrt()).exp()).alias("HR_lo"))
R = R.with_columns((pl.col("candidate") & (pl.col("n_agents")>=5) & (pl.col("lifespan_d")>=7) & (pl.col("uses_agent")>=15)).alias("core"))
R = R.with_columns(pl.when(pl.col("n_adopters")<3).then(pl.lit("too_few_adopters"))
      .when(pl.col("HR_lo")>=10).then(pl.lit("coinage_like"))
      .when(pl.col("HR_cc")>=5).then(pl.lit("mixed"))
      .otherwise(pl.lit("tic_or_plain")).alias("hr_class"))
R.write_parquet("phrase_spread.parquet")
print(R.filter("core").group_by("hr_class").len())
