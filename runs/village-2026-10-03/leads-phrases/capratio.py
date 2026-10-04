# Name-ness: share of agent uses written in Title Case (proper-name usage) + min word zipf.
import polars as pl, re
from wordfreq import zipf_frequency as Z
C = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/"
R = pl.read_parquet("phrase_spread.parquet")
idx = pl.read_parquet("chat_index.parquet").select("i","id","kind")
txt = pl.read_parquet(C+"chat_raw.parquet", columns=["id","text"])
h = pl.read_parquet("chat_hits.parquet").join(idx, on="i").filter(pl.col("kind")=="agent").join(txt, on="id")
keys = dict(zip(R["cid"].to_list(), R["key"].to_list()))
rx = {cid: re.compile(r"(?<![A-Za-z0-9])" + r"[^A-Za-z0-9']+".join(re.escape(w) for w in k.split()) + r"(?![A-Za-z0-9])", re.I) for cid,k in keys.items()}
tot, cap = {}, {}
for cid, t in zip(h["cid"].to_list(), h["text"].to_list()):
    m = rx[cid].search(t or "")
    if not m: continue
    tot[cid] = tot.get(cid,0)+1
    s = m.group(0); ws = re.findall(r"[A-Za-z0-9']+", s)
    if all(w[0].isupper() or w.lower() in ("of","the","and","de","a") or w[0].isdigit() for w in ws): cap[cid] = cap.get(cid,0)+1
R = R.with_columns(pl.col("cid").map_elements(lambda c: cap.get(c,0)/tot[c] if tot.get(c) else None, return_dtype=pl.Float64).alias("cap_ratio"),
                   pl.col("key").map_elements(lambda k: min(Z(w,"en") for w in k.split()), return_dtype=pl.Float64).alias("min_zipf"))
R = R.with_columns(((pl.col("cap_ratio")>=0.7) | (pl.col("min_zipf")<2.5)).alias("invented_form"))
R.write_parquet("phrase_spread.parquet")
print(R.filter("core").group_by("invented_form","hr_class").len().sort("invented_form","hr_class"))
