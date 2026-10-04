import polars as pl, datetime as dt, re
pl.Config.set_tbl_rows(200); pl.Config.set_fmt_str_lengths(60); pl.Config.set_tbl_width_chars(250)
U=dt.timezone.utc
T0=dt.datetime(2026,6,18,20,9,40,tzinfo=U); T1=dt.datetime(2026,6,18,20,10,20,tzinfo=U)
d=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet').sort('time','position')
s=d.filter(pl.col('kind')=='save')
rows=[]
for r in s.filter(pl.col('text').str.contains('(?i)NextWord|CachePoke')).iter_rows(named=True):
    if T0<=r['time']<=T1: continue
    nums=[int(n) for n in re.findall(r'LoopNextWord(\d+)',r['text'])]
    cp=re.findall(r'CachePokeWord(\d+)',r['text']); mn=re.findall(r'MoreNextWord(\d+)',r['text'])
    head=r['text'].strip().split('\n')[0][:55]
    rows.append(dict(time=r['time'],actor=r['actor'],page=r['page'][:22],ip=r['ip16'],head=head,nL=len(nums),lo=min(nums) if nums else None,hi=max(nums) if nums else None,cp=','.join(sorted(set(cp)))[:30],mn=len(mn)))
print(pl.DataFrame(rows))
