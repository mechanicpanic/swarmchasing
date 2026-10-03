# Adoption timing: is an agent's FIRST use of P timed by exposure?
# O/E = (# adopters exposed within 60 min, same room, at first use) / (sum over adopters of the share of their
#        own pre-adoption messages that were exposed)  -> 1.0 = first use not timed by exposure.
import polars as pl
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_width_chars(250)
F = pl.read_parquet("first_use.parquet")
ad = F.filter(pl.col("first_use").is_not_null() & (pl.col("agent")!=pl.col("origin")))
rows=[]
for (ph,pk), d in ad.group_by("phrase","pkind"):
    allA = F.filter(pl.col("phrase")==ph)
    e = d.filter(pl.col("pre_exp_rate").is_not_null())
    O = int(e["exposed_1h_same_room"].sum()); E = float(e["pre_exp_rate"].sum())
    never = d.filter(pl.col("prior_uses_since_arrival")==0)
    rows.append(dict(phrase=ph, kind=pk, users=d.height+1, adopters=d.height,
        no_exposure_since_arrival=never.height,
        first_msg_day_unexposed=d.filter((pl.col("prior_uses_since_arrival")==0)&(pl.col("hours_since_arrival")<48)).height,
        exposed_at_first=O, expected=round(E,1), OE=round(O/E,2) if E>0 else None,
        at_mentioned=int(d["at_exposed"].sum()),
        med_h_since_last_other=round(d["hours_since_last_other"].median() or -1,1),
        exposed_nonadopters=allA.filter(pl.col("first_use").is_null() & (pl.col("pre_exposed_msgs")>0)).height))
r = pl.DataFrame(rows).sort("kind","OE", descending=[False,True])
print(r); r.write_csv("first_use_summary.csv")
# pooled per kind
for pk, d in ad.filter(pl.col("pre_exp_rate").is_not_null()).group_by("pkind"):
    O=d["exposed_1h_same_room"].sum(); E=d["pre_exp_rate"].sum()
    print(pk, "adoptions", d.height, "O",O,"E",round(E,1),"O/E",round(O/E,2), "no-exposure-since-arrival", (d["prior_uses_since_arrival"]==0).sum())
