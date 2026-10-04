import polars as pl, datetime as dt
U=dt.timezone.utc
d=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet').sort('time','position')
s=d.filter(pl.col('kind')=='save')
x=s.filter(pl.col('actor')=='LooFmt606108')
print(x.height, x['time'].min(), x['time'].max(), x['ip16'].n_unique(), x['page'].unique().to_list())
for r in x.head(4).iter_rows(named=True):
    print('---',r['time'],r['ip16'],r['summary'],r['n_added'],r['body_len']); print(r['text'][:1500])
print('distinct texts', x['text'].n_unique())
