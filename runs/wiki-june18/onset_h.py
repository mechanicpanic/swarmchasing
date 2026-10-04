import polars as pl
s=pl.read_parquet('s2.parquet')
df=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet')
dl=df.filter(pl.col('kind')=='delete').with_columns(pl.col('time').dt.truncate('10m').alias('b'))

s=s.filter(pl.col('time').is_between(pl.datetime(2026,6,18,14,time_zone='UTC'),pl.datetime(2026,6,18,22,time_zone='UTC'))).with_columns(pl.col('time').dt.truncate('10m').alias('b'))
h=s.group_by('b').agg(pl.len().alias('all'),(pl.col('wiki')=='dse').sum().alias('dse'),pl.col('s1').sum(),(pl.col('gap')<=10).sum().alias('g10'),pl.col('summary').str.contains(r'17818\d{5}').sum().alias('epoch')).sort('b').join(dl.group_by('b').len().rename({'len':'del'}),on='b',how='left')
for r in h.iter_rows(named=True):
    print(r['b'].strftime('%H:%M'),f"{r['all']:4d} dse={r['dse']:4d} s1={r['s1']:4d} g10={r['g10']:4d} ep={r['epoch']:3d} del={r['del'] or 0:3d}",'#'*(r['all']//10))
