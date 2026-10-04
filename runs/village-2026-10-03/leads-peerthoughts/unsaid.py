import sys, polars as pl
sys.path.insert(0,'../conflicts')
from agents import names_in
from nliload import load
P,done=load()
k=sys.argv[1]; thr=float(sys.argv[2])
A=P.filter((pl.col('n_'+k)>thr)&pl.col('event_text').is_not_null()).explode('subjects')
A=A.with_columns(pl.struct('event_text','subjects').map_elements(lambda r: r['subjects'] in names_in(r['event_text']),return_dtype=pl.Boolean).alias('named_pub'))
print(k,'talk-preceding sents',A.height,'subject named in next public msg',A['named_pub'].mean())
print(A.group_by('agent').agg(pl.len(),pl.col('named_pub').mean().round(2)).filter(pl.col('len')>=20).sort('named_pub'))
A.write_parquet(f'unsaid_{k}.parquet')
for r in A.filter(~pl.col('named_pub')).sample(min(10,A.filter(~pl.col('named_pub')).height),seed=2).iter_rows(named=True):
    print(f"- {r['time'][:10]} {r['agent']} re {r['subjects']}: {r['sent'][:200]}\n     PUB: {r['event_text'][:200]}")
