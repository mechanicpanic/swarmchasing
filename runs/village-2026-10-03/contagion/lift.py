# Mantel-Haenszel within-agent-day lift of using P after exposure (others used P, same room, prior 60 min),
# strata = (agent, day, self-used-P-in-prior-60min). Bootstrap CI by resampling (agent,day) clusters.
import polars as pl, numpy as np, sys
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_width_chars(220)
S = pl.read_parquet(sys.argv[1] if len(sys.argv)>1 else "strata.parquet")
rng = np.random.default_rng(0)

def mh_table(df, expcol="exp", extra_strata=()):
    keys = ["phrase","agent","day","selfrec",*extra_strata]
    t = (df.group_by(keys).agg(
            pl.col("n").filter(pl.col(expcol)).sum().alias("n1"), pl.col("k").filter(pl.col(expcol)).sum().alias("a"),
            pl.col("n").filter(~pl.col(expcol)).sum().alias("n0"), pl.col("k").filter(~pl.col(expcol)).sum().alias("b"))
          .filter((pl.col("n1")>0)&(pl.col("n0")>0))
          .with_columns((pl.col("n1")+pl.col("n0")).alias("N"))
          .with_columns((pl.col("a")*pl.col("n0")/pl.col("N")).alias("num"), (pl.col("b")*pl.col("n1")/pl.col("N")).alias("den")))
    return t

def mh(t, B=300):
    num, den = t["num"].sum(), t["den"].sum()
    rr = num/den if den>0 else float("inf")
    # cluster bootstrap over (agent, day)
    g = t.group_by("agent","day").agg(pl.col("num").sum(), pl.col("den").sum())
    nu, de = g["num"].to_numpy(), g["den"].to_numpy()
    bs=[]
    for _ in range(B):
        ix = rng.integers(0, len(nu), len(nu)); d = de[ix].sum()
        bs.append(nu[ix].sum()/d if d>0 else np.inf)
    lo, hi = np.percentile(bs,[2.5,97.5]) if len(nu) else (np.nan,np.nan)
    return rr, lo, hi

def summarize(S, expcol="exp", label=""):
    rows=[]
    for (ph, pk), df in S.group_by("phrase","pkind"):
        t = mh_table(df, expcol)
        if t.height==0: continue
        rr, lo, hi = mh(t)
        p1 = t["a"].sum()/t["n1"].sum(); p0 = t["b"].sum()/t["n0"].sum()
        rows.append(dict(phrase=ph, kind=pk, strata=t.height, agents=t["agent"].n_unique(), exp_msgs=int(t["n1"].sum()), exp_hits=int(t["a"].sum()),
                         p_exp=round(p1,4), p_unexp=round(p0,4), MH_RR=round(rr,2), lo=round(lo,2), hi=round(hi,2)))
    return pl.DataFrame(rows).sort(["kind","MH_RR"], descending=[False,True])

if __name__=="__main__":
    r = summarize(S); print(r); r.write_csv("lift_by_phrase.csv")
    # pooled by kind
    out=[]
    for pk, df in S.group_by("pkind"):
        t = mh_table(df); rr,lo,hi = mh(t)
        # also without self-recent strata (only messages where A had NOT used P in last hour)
        t2 = t.filter(~pl.col("selfrec")); rr2,lo2,hi2 = mh(t2)
        out.append(dict(kind=pk[0], MH_RR=round(rr,2), lo=round(lo,2), hi=round(hi,2), MH_RR_noself=round(rr2,2), lo2=round(lo2,2), hi2=round(hi2,2), strata=t.height))
    print(pl.DataFrame(out))
