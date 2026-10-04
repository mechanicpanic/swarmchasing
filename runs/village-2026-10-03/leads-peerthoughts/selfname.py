import sys, polars as pl
sys.path.insert(0,'../conflicts')
from agents import names_in
T=(pl.scan_parquet('../conflicts/thoughts.parquet').select('time','agent','thought').unique(['agent','thought']).collect())
SPLIT=r'(?:[^.!?\n]|[.!?][^\s.!?])+[.!?]*'
S=T.with_columns(pl.col('thought').str.extract_all(SPLIT).alias('sent')).drop('thought').explode('sent')
rows=[]
for a in S['agent'].unique().to_list():
    sub=S.filter(pl.col('agent')==a)
    # quick prefilter using the short form of own name
    key=a.replace('Claude ','').split(' (')[0]
    c=sub.filter(pl.col('sent').str.contains(key,literal=True))
    own=[r for r in c.iter_rows(named=True) if a in names_in(r['sent'])]
    rows+= [dict(agent=a,time=r['time'],sent=r['sent'][:400]) for r in own]
D=pl.DataFrame(rows); D.write_parquet('self_named_sents.parquet')
n=T.group_by('agent').len()
g=D.group_by('agent').len().rename({'len':'selfsents'}).join(n,on='agent').with_columns((pl.col('selfsents')/pl.col('len')*1000).round(1).alias('per1k')).sort('per1k',descending=True)
pl.Config.set_tbl_rows(40); print(g)
for pat in [r'(?i)\b(myself|that.s me|which is me|\(me\)|i am|i.m)\b']:
    print(pat, D.filter(pl.col('sent').str.contains(pat)).height)
for r in D.sample(15,seed=4).iter_rows(named=True): print('-',r['agent'],'|',r['sent'][:200])
