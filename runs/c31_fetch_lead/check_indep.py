"""C31 cold-check re-implementation (verifier): sign test, alternative family maps, time-of-day re-pairing null for |lead|.
usage: REPO=<repo root> python runs/c31_fetch_lead/check_indep.py [offset_h]"""
import re, numpy as np, polars as pl
from math import comb
D=__import__("os").environ.get("REPO", ".") + "/data/"
U=pl.read_parquet(D+"transluce/urlquery.parquet").filter(pl.col("disposition")=="included")
W=pl.read_parquet(D+"wiki_msgs.parquet").filter(pl.col("kind")=="add")
UMAP={"SEC county data":"sec","AIHW":"aihw","IHME":"ihme","DataUSA":"datausa","MAX budget documents":"max","Maryland school report cards":"md",
 "UNM digital library":"unm","UNCTAD":"unctad","Thrill Data":"thrill","USAspending":"usasp","Clark economics newsletter":"clark",
 "Digital Public Library of America":"dpla","US Census API":"census"}
KW={"sec":r"sec\.gov/files/county|county\.json","max":r"max\.gov|max\.omb\.gov","md":r"maryland","unm":r"unm\.edu|digitalrepository\.unm",
 "aihw":r"aihw","ihme":r"ihme|healthdata\.org","datausa":r"datausa","unctad":r"unctad","thrill":r"thrill","usasp":r"usaspending",
 "clark":r"clarku","dpla":r"\bdp\.la\b","census":r"census\.gov"}
# alternative strict map: domains only, no page_family prefix
KW_STRICT={"sec":r"sec\.gov/files/county","max":r"max\.gov","aihw":r"aihw\.gov","ihme":r"healthdata\.org","datausa":r"datausa\.io",
 "unctad":r"unctad\.org","usasp":r"usaspending\.gov","clark":r"clarku\.edu","dpla":r"\bdp\.la\b","census":r"census\.gov",
 "md":r"marylandpublicschools|reportcard\.msde","unm":r"digitalrepository\.unm","thrill":r"thrilldata"}
H=3600.0
def wfams(pf,t,mode):
    t=(t or "").lower(); pf=pf or ""
    if mode=="strict": return {f for f,rx in KW_STRICT.items() if re.search(rx,t)}
    fs={f for f in ("aihw","ihme","datausa") if pf.startswith(f)}
    hits={f for f,rx in KW.items() if re.search(rx,t)}
    if mode=="single":  # uq_wiki.py style: page family, else FIRST keyword hit, single label
        if fs: return fs
        for f,rx in KW.items():
            if re.search(rx,t): return {f}
        return set()
    return fs|hits
def build(off,mode,first_only=False):
    ut=U["time"].to_numpy().astype("datetime64[s]").astype(np.int64)-off*3600
    wt=W["time"].to_numpy().astype("datetime64[s]").astype(np.int64)-off*3600
    uf=[UMAP.get(x) for x in U["data_source"].to_list()]
    wf=[wfams(p,t,mode) for p,t in zip(W["page_family"].to_list(),W["text"].to_list())]
    keep=np.ones(len(wt),bool)
    if first_only: keep=np.array(W["first_of_text"].to_list())
    ud=ut//86400; wd=wt//86400
    us={}; ws={}
    for t,d,f in zip(ut,ud,uf):
        if f: us.setdefault((f,d),[]).append(t)
    for t,d,fs,k in zip(wt,wd,wf,keep):
        if k:
            for f in fs: ws.setdefault((f,d),[]).append(t)
    pairs=sorted(set(us)&set(ws))
    return pairs,us,ws,ut,ud,uf,wt,wd,wf
def binom_p(k,n): return sum(comb(n,i) for i in range(k,n+1))/2**n
def report(off,mode,first_only=False,verbose=False):
    pairs,us,ws,ut,ud,uf,wt,wd,wf=build(off,mode,first_only)
    lead=np.array([(min(ws[p])-min(us[p]))/H for p in pairs])
    k=(lead>0).sum(); n=len(lead)
    # time-of-day cross-pair null for |lead|: keep each pair's scan time-of-day, give it another pair's wiki time-of-day
    tu=np.array([min(us[p])%86400 for p in pairs])/H; tw=np.array([min(ws[p])%86400 for p in pairs])/H
    rng=np.random.default_rng(7); real=np.median(np.abs(tw-tu))
    nul=np.array([np.median(np.abs(tw[rng.permutation(n)]-tu)) for _ in range(5000)])
    # N3-like: circular shift each family's scans within the day (own impl)
    n3=[]
    for _ in range(2000):
        l=[]
        for p in pairs:
            s=rng.uniform(0,86400); d0=p[1]*86400
            x=d0+((np.array(us[p])-d0+s)%86400); l.append(abs(min(ws[p])-x.min())/H)
        n3.append(np.median(l))
    n3=np.array(n3)
    print(f"off={off:2d} mode={mode:6s} first_of_text={first_only!s:5s} pairs={n} fams={len({f for f,_ in pairs})} "
          f"uq-first={k}/{n}={k/n:.2f} sign-test p(>=k)={binom_p(k,n):.2f} median lead={np.median(lead):+.2f}h "
          f"|lead| med={np.median(np.abs(lead)):.2f} | tod-cross null mean {nul.mean():.2f} p={(1+(nul<=real).sum())/(1+len(nul)):.4f} (tod real {real:.2f}) "
          f"| N3own mean {n3.mean():.2f} p={(1+(n3<=np.median(np.abs(lead))).sum())/(1+len(n3)):.4f}")
    if verbose:
        for p,l in zip(pairs,lead): print("   ",p[0],np.datetime64(int(p[1])*86400,'s').astype('datetime64[D]'),len(us[p]),len(ws[p]),round(l,2))
for off in (0,12):
    for mode in ("multi","single","strict"):
        report(off,mode,verbose=(off==0 and mode=="multi"))
report(0,"multi",first_only=True)
