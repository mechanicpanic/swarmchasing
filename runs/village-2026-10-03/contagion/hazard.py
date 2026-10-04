# Adoption hazard ratio: among an agent's messages that are "at risk" (after the phrase's village debut, before the
# agent's own first use), how much likelier is the FIRST use in a message exposed (others used P in same room, prior 60 min)
# than in an unexposed one?  Trained-in phrase -> ~ same hazard (HR~1, first use whenever);  village-spread -> HR >> 1.
import polars as pl, numpy as np
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(250); pl.Config.set_fmt_str_lengths(42)
F = pl.concat([pl.read_parquet("first_use.parquet"), pl.read_parquet("first_use_tics.parquet").filter(
        ~pl.col("phrase").is_in(["live and verified","exactly right","absolutely right","standing by","U+2011 non-breaking hyphen","checkmark emoji ✅","party emoji 🎉","load-bearing","you're right"]))], how="diagonal_relaxed")
F = F.filter(pl.col("agent")!=pl.col("origin")).with_columns(
    pl.col("first_use").is_not_null().alias("adopted"),
    pl.col("exposed_1h_same_room").fill_null(False).alias("e1"))
F = F.with_columns(
    (pl.col("pre_exposed_msgs") + pl.col("e1").cast(pl.Int64)).alias("n_exp"),
    (pl.col("pre_msgs") - pl.col("pre_exposed_msgs") + (pl.col("adopted") & ~pl.col("e1")).cast(pl.Int64)).alias("n_unexp"),
    (pl.col("adopted") & pl.col("e1")).alias("ev_exp"), (pl.col("adopted") & ~pl.col("e1")).alias("ev_unexp"))
def hr(d):
    a, n1, b, n0 = d["ev_exp"].sum(), d["n_exp"].sum(), d["ev_unexp"].sum(), d["n_unexp"].sum()
    h1, h0 = a/max(n1,1), b/max(n0,1)
    if a==0 or b==0: lo=hi=np.nan
    else:
        se=np.sqrt(1/a+1/b); lo,hi=(h1/h0)*np.exp(-1.96*se),(h1/h0)*np.exp(1.96*se)
    return dict(adopt_exp=int(a), exp_msgs=int(n1), adopt_unexp=int(b), unexp_msgs=int(n0),
                h_exp_per_1k=round(1000*h1,2), h_unexp_per_1k=round(1000*h0,3), HR=round(h1/h0,1) if h0>0 else None,
                lo=round(lo,1) if lo==lo else None, hi=round(hi,1) if hi==hi else None)
rows=[dict(kind=k, phrases=d["phrase"].n_unique(), **hr(d)) for (k,), d in F.group_by("pkind")]
print(pl.DataFrame(rows).sort("HR"))
per=pl.DataFrame([dict(phrase=p, kind=k, **hr(d)) for (p,k), d in F.group_by("phrase","pkind")]).sort("kind","HR",nulls_last=True)
per.write_csv("adoption_hazard_by_phrase.csv"); print(per)

# MH-pooled HR stratified by phrase, and median per-phrase HR, per kind
def mh_hr(d):
    t = d.group_by("phrase").agg(pl.col("ev_exp").sum().alias("a"), pl.col("n_exp").sum().alias("n1"),
                                 pl.col("ev_unexp").sum().alias("b"), pl.col("n_unexp").sum().alias("n0")).with_columns((pl.col("n1")+pl.col("n0")).alias("N"))
    num=(t["a"]*t["n0"]/t["N"]).sum(); den=(t["b"]*t["n1"]/t["N"]).sum()
    v=((t["a"]+t["b"])*t["n1"]*t["n0"]/t["N"]**2).sum(); se=np.sqrt(v/(num*den)); rr=num/den
    return round(rr,1), round(rr*np.exp(-1.96*se),1), round(rr*np.exp(1.96*se),1)
out=[]
for (k,), d in F.group_by("pkind"):
    rr,lo,hi = mh_hr(d); ph = per.filter(pl.col("kind")==k)["HR"].drop_nulls()
    out.append(dict(kind=k, MH_HR=rr, lo=lo, hi=hi, median_phrase_HR=round(ph.median(),1), phrases_with_zero_unexposed_adoptions=per.filter((pl.col("kind")==k)&pl.col("HR").is_null()).height))
o=pl.DataFrame(out); print(o); o.write_csv("adoption_hazard_by_kind.csv")
