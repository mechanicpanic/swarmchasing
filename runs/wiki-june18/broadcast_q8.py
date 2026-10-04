import polars as pl, datetime as dt
pl.Config.set_tbl_rows(300); pl.Config.set_fmt_str_lengths(50); pl.Config.set_tbl_width_chars(220)
U=dt.timezone.utc
T0=dt.datetime(2026,6,18,20,9,40,tzinfo=U); T1=dt.datetime(2026,6,18,20,10,20,tzinfo=U)
d=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet').sort('time','position')
s=d.filter(pl.col('kind')=='save').with_columns(burst=pl.col('time').is_between(T0,T1)&pl.col('page').str.starts_with('LoopNextWord'),
  head=pl.col('text').str.strip_chars().str.split('\n').list.first().str.slice(0,45))
w=s.filter(pl.col('time').is_between(T0,T1) & ~pl.col('burst'))
print('non-burst saves during burst window:', w.height)
print(w.select('time','actor','page','ip16','summary','head'))
# TryVar counter
tv=s.filter(pl.col('head').str.contains('TryVar'))
print(tv.select('time','actor','page','ip16','head'))
