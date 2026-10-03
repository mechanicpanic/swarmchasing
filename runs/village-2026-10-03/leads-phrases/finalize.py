# Privacy pass: drop candidates that look like person names (census first names + surname/rare token, or human display-name tokens).
import polars as pl, names, os
from wordfreq import zipf_frequency as Z
d = os.path.dirname(names.__file__)
FN = {l.split()[0].lower() for f in ["dist.male.first","dist.female.first"] for l in open(os.path.join(d,f))}
LN = {l.split()[0].lower() for l in open(os.path.join(d,"dist.all.last"))}
R = pl.read_parquet("phrase_spread.parquet")
def person(k, cap):
    w = k.split()
    for i in range(len(w)-1):
        if w[i] in FN and (w[i+1] in LN or Z(w[i+1],"en") < 3.5): return True
    if cap is not None and cap >= 0.7 and len(w)==2 and all(Z(x,"en")<3.0 for x in w): return True
    return False
R = R.with_columns(pl.struct("key","cap_ratio").map_elements(lambda s: person(s["key"], s["cap_ratio"]), return_dtype=pl.Boolean).alias("maybe_person"))
drop = R.filter(pl.col("maybe_person") | pl.col("has_human_name_token"))
print("dropping", drop.height, "person-like/human-name rows")
R = R.filter(~(pl.col("maybe_person") | pl.col("has_human_name_token"))).drop("maybe_person","has_human_name_token")
R.write_parquet("phrase_spread.parquet")
A = pl.read_parquet("adoptions.parquet").join(R.select("cid"), on="cid", how="semi"); A.write_parquet("adoptions.parquet")
print(R.height, "rows kept;", R.filter("core").height, "core;", R.filter(pl.col("core") & pl.col("invented_form")).height, "core+invented_form")
