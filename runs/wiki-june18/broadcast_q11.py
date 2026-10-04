import polars as pl, datetime as dt, numpy as np
pl.Config.set_tbl_rows(70); pl.Config.set_tbl_width_chars(200)
U=dt.timezone.utc
T0=dt.datetime(2026,6,18,20,9,40,tzinfo=U); T1=dt.datetime(2026,6,18,20,10,20,tzinfo=U)
d=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet').sort('time','position')
s=d.filter(pl.col('kind')=='save').with_columns(burst=pl.col('time').is_between(T0,T1)&pl.col('page').str.starts_with('LoopNextWord'))
b=s.filter('burst'); nb=s.filter(~pl.col('burst'))
win=nb.filter(pl.col('time').is_between(T0-dt.timedelta(minutes=10),T1+dt.timedelta(minutes=10)))
act=win.group_by('actor').len().rename({'len':'n_ctx'})
bl=b.group_by('actor').len().rename({'len':'n_burst'})
j=bl.join(act,on='actor',how='full',coalesce=True).fill_null(0)
print('burst labels',bl.height,'of which active +-10min outside burst', j.filter((pl.col('n_burst')>0)&(pl.col('n_ctx')>0)).height)
print('labels active +-10min', act.height, 'of which appear in burst', j.filter((pl.col('n_burst')>0)&(pl.col('n_ctx')>0)).height)
jj=j.filter(pl.col('n_ctx')>0)
print('spearman-ish corr n_burst vs n_ctx (active labels):', np.corrcoef(jj['n_burst'].rank(),jj['n_ctx'].rank())[0,1])
print(j.sort('n_ctx',descending=True).head(25))
# the 3 never-seen labels
for a in ['GuestResearch131157','AgentResearchJune','UserTTT']:
    print(a, b.filter(pl.col('actor')==a).select('time','page','ip16').to_dicts())
    print('  similar label names elsewhere:', s.filter(pl.col('actor').str.contains(a[:-3]) & (pl.col('actor')!=a))['actor'].unique().to_list()[:8])
# all-data: any save labelled with these in labels.jsonl?
