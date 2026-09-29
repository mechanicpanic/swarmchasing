"""Lead-lag between urlquery reports and wiki messages on one stream (data/uq_wiki.parquet), per shared family.
Count = urlquery reports of family f followed within W by a wiki message of the same family (one chain per report), and the reverse.
Null = the same counts with every urlquery time shifted by ±1..±14 days (28 shifts). Inline engine; the server is not needed."""
import statistics, polars as pl
from prismql import PrismQLEngine
from prismql.backends.memory import MemoryBackend
df = pl.read_parquet('data/uq_wiki.parquet').select('id', 'time', 'source', 'family')
FAMS = ['sec-county', 'datausa', 'ihme', 'max-budget', 'aihw']; W = '6 hours'
def docs_for(shift_days):
    d = df.with_columns(pl.when(pl.col('source') == 'urlquery').then(pl.col('time') + pl.duration(days=shift_days)).otherwise(pl.col('time')).alias('time')).sort('time')
    return [dict(r, time=r['time'].strftime('%Y-%m-%dT%H:%M:%SZ'), timestamp=r['time'].strftime('%Y-%m-%dT%H:%M:%SZ')) for r in d.to_dicts()]
def counts(docs):
    eng = PrismQLEngine(search_backend=MemoryBackend(docs, id_field='id'), timestamp_field='time'); out = {}
    for f in FAMS:
        a = f'SELECT field(source, urlquery) AND field(family, "{f}") FOLLOWED_BY field(source, wiki) AND field(family, "{f}") DURING {W} AGGREGATE count()'
        b = f'SELECT field(source, wiki) AND field(family, "{f}") FOLLOWED_BY field(source, urlquery) AND field(family, "{f}") DURING {W} AGGREGATE count()'
        out[f] = (eng.execute(a).to_dict()['value'], eng.execute(b).to_dict()['value'])
    return out
real = counts(docs_for(0))
nulls = [counts(docs_for(s)) for s in [*range(-14, 0), *range(1, 15)]]
n_by = df.group_by('source', 'family').len()
print(f"window {W}; null = urlquery shifted ±1..14 days (28)")
print(f"{'family':12s} {'uq n':>6s} {'wiki n':>6s} | {'uq→wiki real':>12s} {'null med':>8s} {'null max':>8s} | {'wiki→uq real':>12s} {'null med':>8s} {'null max':>8s}")
for f in FAMS:
    nu = n_by.filter((pl.col('source') == 'urlquery') & (pl.col('family') == f))['len'].sum(); nw = n_by.filter((pl.col('source') == 'wiki') & (pl.col('family') == f))['len'].sum()
    a = [x[f][0] for x in nulls]; b = [x[f][1] for x in nulls]
    print(f"{f:12s} {nu:6d} {nw:6d} | {real[f][0]:12d} {statistics.median(a):8.1f} {max(a):8d} | {real[f][1]:12d} {statistics.median(b):8.1f} {max(b):8d}")
