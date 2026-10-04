import polars as pl, datetime as dt, re
pl.Config.set_tbl_rows(200); pl.Config.set_fmt_str_lengths(140); pl.Config.set_tbl_width_chars(300)
U=dt.timezone.utc
d=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet').sort('time','position')
T0=dt.datetime(2026,6,18,20,9,40,tzinfo=U); T1=dt.datetime(2026,6,18,20,10,20,tzinfo=U)
pats=['LoopNextWord','CachePokeWord','NextRawChild','predicted child','InvYear','InvMetaFilters','predicted','NextWord','RawChild','Loop child','POKECHAIN','CachePoke','PokeNext','PointerFast','WIN13']
s=d.filter(pl.col('kind')=='save')
for p in pats:
    m=s.filter(pl.col('text').str.contains('(?i)'+re.escape(p)) | pl.col('summary').fill_null('').str.contains('(?i)'+re.escape(p)) | pl.col('page').str.contains('(?i)'+re.escape(p)))
    pre=m.filter(pl.col('time')<T0); inn=m.filter(pl.col('time').is_between(T0,T1)); post=m.filter(pl.col('time')>T1)
    print(f'== {p}: pre {pre.height} in {inn.height} post {post.height}; first {m["time"].min()} last {m["time"].max()}')
    print(pre.select('time','actor','page','ip16','summary').head(12))
    print(post.select('time','actor','page','ip16','summary').head(12))
