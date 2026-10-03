import polars as pl, sys
# usage: show.py "<thinker or *>" "<subject or *>" "<polars filter expr>" n [pub]
a,s,expr,n=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4]); pub=len(sys.argv)>5
P=pl.read_parquet('peer_sents_all_scores.parquet').filter(pl.col('nw')>=6)
try:
    N=pl.read_parquet('nli_pool.parquet'); P=P.join(N,on='rid',how='left')
except Exception: pass
P=P.with_columns((pl.col('e_anger')+pl.col('e_disgust')).alias('neg'))
if a!='*': P=P.filter(pl.col('agent')==a)
if s!='*': P=P.filter(pl.col('subjects').list.contains(s))
P=P.filter(eval(expr))
print('matches',P.height)
for r in P.sample(min(n,P.height),seed=7).sort('time').iter_rows(named=True):
    print(f"- {r['time'][:16]} {r['agent']} [{r['of']}] {r['sent'][:260]}")
    if pub and r['event_text']: print(f"     PUBLIC: {r['event_text'][:260]}")
