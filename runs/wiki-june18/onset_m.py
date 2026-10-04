import polars as pl, re, sys
s=pl.read_parquet('s2.parquet').sort('time')
pat=sys.argv[1]; lim=int(sys.argv[2]); t0=sys.argv[3] if len(sys.argv)>3 else '2026-01-01'; t1=sys.argv[4] if len(sys.argv)>4 else '2027-01-01'
s=s.filter(pl.col('time')>=pl.lit(t0).str.to_datetime(time_zone='UTC'), pl.col('time')<=pl.lit(t1).str.to_datetime(time_zone='UTC'))
seen=set();n=0
for r in s.iter_rows(named=True):
    t=(r['text'] or '')+' || SUM: '+(r['summary'] or '')
    m=re.search(pat,t)
    if not m: continue
    snip=t[max(0,m.start()-160):m.end()+200].replace('\n',' ')
    if snip in seen: continue
    seen.add(snip); n+=1
    print(f"[{r['time']:%m-%d %H:%M:%S}] {r['actor']} @ {r['page']} (s1={r['s1']}) :: …{snip}…\n")
    if n>=lim: break
