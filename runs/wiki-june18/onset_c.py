import polars as pl
pl.Config.set_tbl_rows(100); pl.Config.set_fmt_str_lengths(80); pl.Config.set_tbl_width_chars(250)
df=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet')
s=df.filter(pl.col('kind')=='save').sort('time','position')
s=s.with_columns(pl.col('time').dt.date().alias('d'))
s=s.with_columns(pl.col('time').diff().dt.total_seconds().over('actor').alias('gap'))
# runs per label: break if gap>10s
s=s.with_columns(((pl.col('gap').is_null())|(pl.col('gap')>10)).cast(pl.Int32).cum_sum().over('actor').alias('run'))
r=s.group_by('actor','run').agg(pl.len().alias('n'),pl.col('time').min().alias('t0'),pl.col('time').max().alias('t1'),pl.col('text').n_unique().alias('ntext'),pl.col('page').n_unique().alias('npage'),pl.col('wiki').first(),pl.col('ip16').n_unique().alias('nip'),pl.col('summary').first())
print(r['n'].value_counts().sort('n'))
print(r.filter(pl.col('n')>=5).sort('t0').head(60))
s.write_parquet('s.parquet'); r.write_parquet('r.parquet')
