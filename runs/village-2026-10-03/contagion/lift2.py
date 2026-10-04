# Within-agent exposure lift (Mantel-Haenszel rate ratio) with controls.
# Main spec: strata = (phrase, agent, day, selfrec, humrec, act); only messages where A had NOT used P in prior hour
# ("noself") and NO human spoke in the room in prior hour ("nohum"): isolates agent->agent exposure.
import polars as pl, numpy as np, sys
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(250); pl.Config.set_fmt_str_lengths(45)
rng = np.random.default_rng(0)
KEYS = ["phrase","agent","day","hour","selfrec","humrec","act"]

def mh_table(df, expcol="exp", keys=KEYS):
    return (df.group_by(keys).agg(
            pl.col("n").filter(pl.col(expcol)).sum().alias("n1"), pl.col("k").filter(pl.col(expcol)).sum().alias("a"),
            pl.col("n").filter(~pl.col(expcol)).sum().alias("n0"), pl.col("k").filter(~pl.col(expcol)).sum().alias("b"))
          .filter((pl.col("n1")>0)&(pl.col("n0")>0)).with_columns((pl.col("n1")+pl.col("n0")).alias("N"))
          .with_columns((pl.col("a")*pl.col("n0")/pl.col("N")).alias("num"), (pl.col("b")*pl.col("n1")/pl.col("N")).alias("den")))

def mh(t, B=300, cluster=("agent","day")):
    # point estimate + Greenland-Robins 95% CI (treats messages as independent; see bootstrap in mh_boot)
    num, den = t["num"].sum(), t["den"].sum()
    if num==0 or den==0: return (float("nan") if den==0 else 0.0), np.nan, np.nan
    rr = num/den
    v = (t["a"]+t["b"])*t["n1"]*t["n0"]/(t["N"]**2)
    se = np.sqrt(v.sum()/(num*den))
    return rr, rr*np.exp(-1.96*se), rr*np.exp(1.96*se)

def mh_boot(t, B=300, cluster=("agent","day")):
    num, den = t["num"].sum(), t["den"].sum()
    rr = num/den if den>0 else float("nan")
    g = t.group_by(*cluster).agg(pl.col("num").sum(), pl.col("den").sum())
    nu, de = g["num"].to_numpy(), g["den"].to_numpy()
    if len(nu)==0: return rr, np.nan, np.nan
    ix = rng.integers(0, len(nu), (B, len(nu)))
    bs = nu[ix].sum(1)/np.maximum(de[ix].sum(1), 1e-12)
    return rr, *np.percentile(bs, [2.5, 97.5])

def spec(S, name):
    if name=="crude_day":  return S, "exp", ["phrase","agent","day","selfrec"]
    if name=="full":       return S, "exp", KEYS
    if name=="clean":      return S.filter(~pl.col("selfrec") & ~pl.col("humrec") & ~pl.col("exp_hum")), "exp", KEYS
    raise ValueError

def by_phrase(S, specname="clean"):
    S2, e, keys = spec(S, specname); rows=[]
    for (ph, pk), df in S2.group_by("phrase","pkind"):
        t = mh_table(df, e, keys)
        if t.height==0 or t["a"].sum()+t["b"].sum()==0: continue
        rr, lo, hi = mh(t)
        rows.append(dict(phrase=ph, kind=pk, agents=t["agent"].n_unique(), exp_msgs=int(t["n1"].sum()), exp_hits=int(t["a"].sum()),
            unexp_hits=int(t["b"].sum()), p_exp=round(t["a"].sum()/t["n1"].sum(),4), p_unexp=round(t["b"].sum()/t["n0"].sum(),4),
            RR=round(rr,2), lo=round(lo,2), hi=round(hi,2)))
    return pl.DataFrame(rows).sort(["kind","RR"], descending=[False,True], nulls_last=True)

def by_kind(S, specname="clean"):
    S2, e, keys = spec(S, specname); out=[]
    for (pk,), df in S2.group_by("pkind"):
        t = mh_table(df, e, keys); rr,lo,hi = mh(t)
        out.append(dict(kind=pk, spec=specname, RR=round(rr,2), lo=round(lo,2), hi=round(hi,2), exp_hits=int(t["a"].sum()), phrases=t["phrase"].n_unique()))
    return pl.DataFrame(out)

if __name__=="__main__":
    for f in sys.argv[1:]:
        S = pl.read_parquet(f)
        print("=====", f)
        print(pl.concat([by_kind(S, s) for s in ["crude_day","full","clean"]]).sort("kind","spec"))
        r = by_phrase(S, "clean"); print(r); r.write_csv(f.replace(".parquet","_lift_clean.csv").replace("strata","lift"))
