import polars as pl, datetime as dt
pl.Config.set_tbl_rows(60); pl.Config.set_fmt_str_lengths(60); pl.Config.set_tbl_width_chars(220)
U=dt.timezone.utc
d=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet').sort('time','position')
s=d.filter((pl.col('kind')=='save')&pl.col('time').is_between(dt.datetime(2026,6,18,16,tzinfo=U),dt.datetime(2026,6,19,2,tzinfo=U)))
s=s.with_columns(head=pl.col('text').str.strip_chars().str.split('\n').list.first().str.replace_all(r'\d+','#').str.slice(0,50))
g=s.filter(pl.col('head').str.len_chars()>8).group_by('head').agg(pl.len().alias('n'),pl.col('actor').n_unique().alias('labels'),pl.col('ip16').n_unique().alias('ip16s'),pl.col('time').min().alias('t0'),pl.col('time').max().alias('t1'),pl.col('actor').unique().head(6).alias('ex'))
print(g.filter(pl.col('labels')>=3).sort('labels',descending=True).head(40))
for r in s.filter(pl.col('head').str.contains('TryVar')).head(3).iter_rows(named=True): print(r['actor'], repr(r['text'][:300]))
