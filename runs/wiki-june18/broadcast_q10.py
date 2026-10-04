import polars as pl, datetime as dt
pl.Config.set_tbl_rows(40); pl.Config.set_fmt_str_lengths(40); pl.Config.set_tbl_width_chars(200)
U=dt.timezone.utc
d=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet').sort('time','position')
s=d.filter((pl.col('kind')=='save')&pl.col('time').is_between(dt.datetime(2026,6,18,16,tzinfo=U),dt.datetime(2026,6,19,2,tzinfo=U)))
x=s.filter(pl.col('text').str.contains(r'= DZFASTMD \d+ =')).with_columns(n=pl.col('text').str.extract(r'DZFASTMD (\d+)').cast(pl.Int64))
print(x.select('time','actor','page','ip16','n').head(25))
r=x.select(pl.col('time').rank(),pl.col('n').rank()); import numpy as np
print('spearman', np.corrcoef(r['time'],r['n'])[0,1], 'labels',x['actor'].n_unique(),'pages',x['page'].n_unique())
# label vs ip16 stickiness
a=s.select('time','actor','ip16').to_dicts()
same_ip=[];base=[]
last_by_ip={}
for i,r in enumerate(a):
    p=last_by_ip.get(r['ip16'])
    if p and (r['time']-p['time']).total_seconds()<120: same_ip.append(p['actor']==r['actor'])
    if i>0: base.append(a[i-1]['actor']==r['actor'])
    last_by_ip[r['ip16']]=r
print('P(same label | prev save same ip16 <120s)', np.mean(same_ip), len(same_ip), ' P(same label as previous save overall)', np.mean(base))
