import sys, polars as pl
from nliload import load
P,done=load(); k=sys.argv[1]; thr=float(sys.argv[2])
A=P.filter(pl.col('n_'+k)>thr)
print(k,'n>',thr,A.height)
X=A.explode('subjects')
print(X.group_by('subjects').len().sort('len',descending=True).head(8).rows())
print(X.group_by('agent').len().sort('len',descending=True).head(8).rows())
print(X.group_by('agent','subjects').len().sort('len',descending=True).head(10).rows())
for r in A.sample(min(14,A.height),seed=11).sort('time').iter_rows(named=True): print(f"- {r['time'][:10]} {r['agent']} [{r['n_'+k]:.2f}] {r['sent'][:190]}")
