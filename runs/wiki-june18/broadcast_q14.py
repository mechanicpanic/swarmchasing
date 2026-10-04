import polars as pl, datetime as dt, re, urllib.parse
U=dt.timezone.utc
d=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet').sort('time','position')
s=d.filter(pl.col('kind')=='save')
def show(cond,label,n=1,k=700):
    x=s.filter(cond)
    print(f'##### {label}: {x.height} saves, labels {x["actor"].n_unique()} ({x["actor"].value_counts().sort("count",descending=True).head(4).rows()}), ip16s {x["ip16"].n_unique()}, {x["time"].min()} .. {x["time"].max()}')
    for r in x.head(n).iter_rows(named=True):
        t=re.sub(r'https?://\S+','<URL>',urllib.parse.unquote(r['text'] or ''))
        print('--',r['time'],r['actor'],r['page'],r['summary']); print(t[:k])
show(pl.col('text').str.contains('CACHED MD SEC WORKING'),'CACHED MD SEC WORKING')
show(pl.col('text').str.contains('POKECHAIN'),'POKECHAIN',k=500)
show(pl.col('text').str.contains('POINTERFAST'),'POINTERFAST')
show(pl.col('text').str.contains('WIN13'),'WIN13')
show(pl.col('text').str.contains('MINE QUERY MD SUCCESS'),'MINE QUERY MD SUCCESS')
show(pl.col('text').str.contains('CACHE POKE CREATED'),'CACHE POKE CREATED',k=500)
