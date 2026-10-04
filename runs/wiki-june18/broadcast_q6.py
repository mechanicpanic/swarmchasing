import polars as pl, datetime as dt, collections
pl.Config.set_tbl_rows(80); pl.Config.set_fmt_str_lengths(70); pl.Config.set_tbl_width_chars(250)
U=dt.timezone.utc
T0=dt.datetime(2026,6,18,20,9,40,tzinfo=U); T1=dt.datetime(2026,6,18,20,10,20,tzinfo=U)
d=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet').sort('time','position')
s=d.filter(pl.col('kind')=='save')
b=s.filter(pl.col('time').is_between(T0,T1) & pl.col('page').str.starts_with('LoopNextWord')).with_columns(n=pl.col('page').str.extract(r'(\d+)$').cast(pl.Int64))
print(b['time_grade'].value_counts())
print('mod20', collections.Counter((b['n']-100000)%20).most_common(10))
print('n range', b['n'].min(), b['n'].max())
blocks=sorted(set(((b['n']-100000)//20).to_list())); print('blocks',len(blocks), blocks[:5], blocks[-5:])
# per-second rate
print(b.group_by(pl.col('time').dt.truncate('5s')).len().sort('time'))
# label first-seen
first=s.group_by('actor').agg(pl.col('time').min().alias('first'),pl.col('time').max().alias('last'),pl.len().alias('n_all'))
lab=b.group_by('actor').agg(pl.len().alias('n_burst'),pl.col('ip16').n_unique().alias('ips')).join(first,on='actor').sort('n_burst',descending=True)
print(lab)
print('ip16 burst unique',b['ip16'].n_unique(), 'top', b['ip16'].value_counts().sort('count',descending=True).head(8))
print('ip /8', b['ip16'].str.split('.').list.first().value_counts().sort('count',descending=True))
