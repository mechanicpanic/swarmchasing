import json, re, polars as pl
from agents import AGENTS, LAB
C=pl.read_parquet('/Users/phosphorus/projects/prismql-data/ai-village/corpus/chat_raw.parquet',columns=['id','time','agent','text','room'])
txt=dict(zip(C['id'],C['text']))
D=json.load(open('dicts.json'))
def rx(words): return re.compile(r'(?i)(?<!\w)('+'|'.join(re.escape(w).replace("'", "['’]") for w in words)+r')(?!\w)')
CON, PUSH = rx(D['concede']), rx(D['pushback'])
agents=set(AGENTS['agent'])
rows=[]
for fn,ans in [('corrections.jsonl',True),('corrections_unanswered.jsonl',False)]:
    for l in open(fn):
        g=json.loads(l); b=g['bindings']
        if len(b)!=1: continue
        a,bb=b[0]['a'],b[0]['b']
        if bb not in agents or a==bb: continue
        ctext=txt[g['ids'][0]]; rtext=txt[g['ids'][1]] if ans else None
        rows.append(dict(cid=g['ids'][0], time=g['times'][0][:19], a=a, b=bb, answered=ans, ctext=ctext, rtext=rtext,
            concede=bool(rtext and CON.search(rtext)), pushback=bool(rtext and PUSH.search(rtext))))
R=pl.DataFrame(rows).unique('cid',keep='first')
R=R.with_columns(pl.col('a').replace_strict(LAB).alias('lab_a'),pl.col('b').replace_strict(LAB).alias('lab_b'))
R.write_parquet('corrections.parquet')
print(R.height, R.select(pl.col('answered').mean(), pl.col('concede').mean(), pl.col('pushback').mean()))
print(R.filter('answered').select(pl.col('concede').mean(),pl.col('pushback').mean()))
