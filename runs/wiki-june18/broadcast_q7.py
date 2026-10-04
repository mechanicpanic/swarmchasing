import polars as pl, datetime as dt
pl.Config.set_tbl_rows(120); pl.Config.set_fmt_str_lengths(70); pl.Config.set_tbl_width_chars(250)
U=dt.timezone.utc
T0=dt.datetime(2026,6,18,20,9,40,tzinfo=U); T1=dt.datetime(2026,6,18,20,10,20,tzinfo=U)
d=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet').sort('time','position')
s=d.filter(pl.col('kind')=='save').with_columns(burst=pl.col('time').is_between(T0,T1)&pl.col('page').str.starts_with('LoopNextWord'),
  head=pl.col('text').str.strip_chars().str.split('\n').list.first().str.slice(0,60))
w=s.filter(pl.col('time').is_between(T0-dt.timedelta(seconds=60),T1+dt.timedelta(seconds=60)) & ~pl.col('burst'))
print('non-burst saves in +-60s window'); print(w.select('time','actor','page','ip16','summary','head'))
for a in ['Agent0AddJS','AgentMassRefUF155300','DataResearchAgent','AgentTesterQ','Agent008HelperMD','AgentReplaceProxy']:
    x=s.filter((pl.col('actor')==a)&~pl.col('burst')&pl.col('time').is_between(T0-dt.timedelta(hours=1),T1+dt.timedelta(hours=1)))
    print('=====',a, x.height, 'distinct heads', x['head'].n_unique())
    print(x.select('time','page','ip16','summary','body_len','head'))
