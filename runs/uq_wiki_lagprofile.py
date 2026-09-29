"""Lag profile: shift urlquery by L hours (L = -12..+12) and count urlquery reports of family f with a wiki message of f
within 1 hour AFTER them. If urlquery leads the wiki by k hours, the count peaks at L = +k (shifting urlquery later aligns it)."""
import polars as pl
from prismql import PrismQLEngine
from prismql.backends.memory import MemoryBackend
df = pl.read_parquet('data/uq_wiki.parquet').select('id', 'time', 'source', 'family').filter(pl.col('family').is_in(['sec-county', 'ihme', 'max-budget']))
res = {}
for L in range(-12, 13):
    d = df.with_columns(pl.when(pl.col('source') == 'urlquery').then(pl.col('time') + pl.duration(hours=L)).otherwise(pl.col('time')).alias('time')).sort('time')
    docs = [dict(r, time=r['time'].strftime('%Y-%m-%dT%H:%M:%SZ')) for r in d.to_dicts()]
    eng = PrismQLEngine(search_backend=MemoryBackend(docs, id_field='id'), timestamp_field='time')
    res[L] = {f: eng.execute(f'SELECT field(source, urlquery) AND field(family, "{f}") FOLLOWED_BY field(source, wiki) AND field(family, "{f}") DURING 1 hour AGGREGATE count()').to_dict()['value'] for f in ['sec-county', 'ihme', 'max-budget']}
print('shift of urlquery (h) | sec-county | ihme | max-budget')
for L, v in res.items(): print(f"{L:+4d}  {v['sec-county']:5d} {'#'*(v['sec-county']//10):46s} {v['ihme']:5d} {v['max-budget']:5d}")
