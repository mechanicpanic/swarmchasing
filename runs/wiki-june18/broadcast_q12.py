import polars as pl, datetime as dt, difflib, itertools, collections
pl.Config.set_tbl_rows(70); pl.Config.set_fmt_str_lengths(70); pl.Config.set_tbl_width_chars(220)
U=dt.timezone.utc
T0=dt.datetime(2026,6,18,20,9,40,tzinfo=U); T1=dt.datetime(2026,6,18,20,10,20,tzinfo=U)
d=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet').sort('time','position')
s=d.filter(pl.col('kind')=='save').with_columns(burst=pl.col('time').is_between(T0,T1)&pl.col('page').str.starts_with('LoopNextWord'))
b=s.filter('burst')
tpl=b['text'][0]
for pg in ['LoopNextWord101660','LoopNextWord100380','LoopNextWord102330','LoopNextWord102320']:
    t=s.filter((pl.col('page')==pg))['text'][0]
    print('==',pg, 'similarity to burst', round(difflib.SequenceMatcher(None,t,tpl).ratio(),3)); 
    import urllib.parse; print(urllib.parse.unquote(t)[:900])
# run lengths
labs=b['actor'].to_list(); runs=[len(list(g)) for k,g in itertools.groupby(labs)]
print('runs', collections.Counter(runs))
# label recency
pre=s.filter((pl.col('time')<T0)&~pl.col('burst')).group_by('actor').agg(pl.col('time').max().alias('last_pre'))
r=b.group_by('actor').len().join(pre,on='actor',how='left').with_columns(gap_min=((pl.lit(T0)-pl.col('last_pre')).dt.total_minutes()))
print(r.select(pl.col('gap_min').is_null().sum().alias('never_before'), (pl.col('gap_min')<=10).sum().alias('<=10m'), ((pl.col('gap_min')>10)&(pl.col('gap_min')<=120)).sum().alias('10m-2h'),(pl.col('gap_min')>120).sum().alias('>2h')))
# ip16 distribution comparison
ev=s.filter(pl.col('time').is_between(dt.datetime(2026,6,18,19,tzinfo=U),dt.datetime(2026,6,18,22,tzinfo=U))&~pl.col('burst'))
eb=set(b['ip16']); ee=set(ev['ip16'])
print('burst ip16s',len(eb),'also seen in other saves 19-22h',len(eb&ee),'; evening other ip16s',len(ee))
f1=ev['ip16'].str.split('.').list.first().value_counts(normalize=True).sort('proportion',descending=True).head(6); print(f1)
