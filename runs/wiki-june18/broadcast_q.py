import polars as pl
pl.Config.set_tbl_rows(40); pl.Config.set_fmt_str_lengths(60); pl.Config.set_tbl_width_chars(220)
s=pl.read_parquet('s2.parquet')
w=s.filter(pl.col('page')=='WillkommenImWiki')
print(w.sort('time').head(3).select('time','actor','summary'))
print(w.group_by(pl.col('time').dt.truncate('20m')).agg(pl.len(),pl.col('actor').n_unique().alias('labels'),pl.col('s1').sum()).sort('time').filter(pl.col('time')>=pl.datetime(2026,6,18,time_zone='UTC')))
p=s.filter(pl.col('summary').str.contains(r'(?i)persist')).sort('time')
print(p.head(8).select('time','actor','page','summary','s1'))
