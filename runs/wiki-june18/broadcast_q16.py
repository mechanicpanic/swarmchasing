import polars as pl, datetime as dt
pl.Config.set_tbl_rows(60); pl.Config.set_fmt_str_lengths(55); pl.Config.set_tbl_width_chars(220)
U=dt.timezone.utc
T0=dt.datetime(2026,6,18,20,9,40,tzinfo=U); T1=dt.datetime(2026,6,18,20,10,20,tzinfo=U)
d=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet').sort('time','position')
s=d.filter(pl.col('kind')=='save').with_columns(burst=pl.col('time').is_between(T0,T1)&pl.col('page').str.starts_with('LoopNextWord'),head=pl.col('text').str.strip_chars().str.split('\n').list.first().str.slice(0,50))
for a in ['OpenAIMass2026','AgentSaveFinal7','LooFmt606108','DataResearchAgent']:
    x=s.filter((pl.col('actor')==a)&~pl.col('burst')&pl.col('time').is_between(T0-dt.timedelta(minutes=90),T1+dt.timedelta(minutes=60)))
    print('=====',a,x.height); print(x.select('time','page','ip16','summary','body_len','head'))
