"""verify_chain.jsonl (PrismQL: X speaks, then within 1h another agent @X with a verification phrase) -> verify.parquet; adds verify_n / verify_refute_n to pair_weekly."""
import json, polars as pl
A='/Users/phosphorus/projects/prismql-data/ai-village/corpus/'
rows={}
for l in open('verify_chain.jsonl'):
    g=json.loads(l); b=g.get('bindings') or []
    if len(b)!=1: continue
    vid=g['ids'][1]; x=b[0]['x']
    rows.setdefault((vid,x), dict(vid=vid, x=x, claim_id=g['ids'][0]))  # nearest-first claim kept (groups ordered by first event; take latest below)
    rows[(vid,x)]['claim_id']=g['ids'][0]  # later group = later claim = nearest earlier X message
V=pl.DataFrame(list(rows.values()))
C=pl.read_parquet(A+'chat_raw.parquet',columns=['id','time','agent','text'])
V=V.join(C.rename({'id':'vid','agent':'verifier','text':'vtext'}),on='vid').join(C.select(pl.col('id').alias('claim_id'),pl.col('text').alias('ctext')),on='claim_id')
REF=r"(?i)(doesn['’]t exist|does not exist|not found|404|incorrect|isn['’]t correct|not correct|that['’]s wrong|is wrong|false positive|can['’]t reproduce|cannot reproduce|doesn['’]t match|does not match|not accurate|inaccurate|fabricated|hallucinated|correction|discrepancy|actually (shows|is|has)|still broken|not (yet )?(live|deployed|merged|visible)|unable to (find|verify|confirm)|could not (find|verify|confirm)|couldn['’]t (find|verify|confirm)|but (it|the|I))"
V=V.with_columns(pl.col('vtext').str.contains(REF).alias('refute'), pl.col('time').dt.truncate('1w').alias('week'))
M=pl.read_parquet('msgs.parquet',columns=['id','dup'])
V=V.join(M.rename({'id':'vid'}),on='vid',how='left').filter(~pl.col('dup').fill_null(False))
V.drop('dup').write_parquet('verify.parquet'); print(V.height, V['refute'].mean())
W=pl.read_parquet('pair_weekly_base.parquet')
v=V.group_by(pl.col('verifier').alias('src'),pl.col('x').alias('dst'),'week').agg(pl.len().alias('verify_n'),pl.col('refute').sum().alias('verify_refute_n'))
W=W.join(v,on=['src','dst','week'],how='left').fill_null(0)
W.write_parquet('pair_weekly.parquet'); print(W.columns, W.height)
