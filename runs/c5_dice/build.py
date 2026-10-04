"""C5: build the per-(agent, day) roll table from the hand-read table.py; every id and value is checked against the data.
usage (from runs/c5_dice): uv run python build.py && uv run python stats.py   — CSV goes to results/ (gitignored)."""
import os
import re, polars as pl
from load import w, datetime, timezone
from table import T
g=w.filter(pl.col('time')>=datetime(2026,3,5,17,tzinfo=timezone.utc)).with_columns(pl.col('time').dt.strftime('%m-%d').alias('d'))
CMD=re.compile(r'(?i)(\$RANDOM|RANDOM\s*%|shuf\s+-i|randint|python3?\b|python script|\bbash\b|terminal shows|ran the script|/dev/urandom|echo \$\(\()')
rows=[]
for (day,ag,pv,pid,pk,ev,pubv,pubid,role,notes) in T:
    r=dict(day="2026-"+day,agent=ag,priv_value=pv,priv_id=None,priv_kind=pk,priv_time=None,evidence=None,pub_value=pubv,pub_id=None,pub_time=None,pub_role=role,notes=notes)
    if pid:
        m=g.filter(pl.col('id').str.starts_with(pid)&(pl.col('kind')==pk))
        assert m.height>=1,(day,ag,pid,pk)
        x=m.row(0,named=True); r['priv_id']=x['id']; r['priv_time']=x['time'].strftime('%H:%M:%S')
        t=x['text']
        if pv is not None and not re.search(rf'(?<![\d#.]){pv}(?![\d])',t): print('WARN value not in text',day,ag,pid)
        if ev: r['evidence']=ev
        elif pv is None: r['evidence']='none'
        elif CMD.search(t): r['evidence']='cmd'
        else:
            st=g.filter((pl.col('agent')==ag)&(pl.col('d')==day)&(pl.col('kind')=='START_USING_COMPUTER')&(pl.col('time')<=x['time'])&pl.col('text').str.contains(r'(?i)\broll|d6|dice'))
            r['evidence']='session' if st.height else 'asserted'
    else:
        r['evidence']='none'
    if pubid:
        m=g.filter(pl.col('id').str.starts_with(pubid)&(pl.col('kind')=='AGENT_TALK'))
        assert m.height>=1,(day,ag,pubid)
        x=m.row(0,named=True); r['pub_id']=x['id']; r['pub_time']=x['time'].strftime('%H:%M:%S')
        if pubv is not None and not re.search(rf'(?<![\d#.]){pubv}(?![\d])',x['text']): print('WARN pub value not in text',day,ag,pubid)
    rows.append(r)
df=pl.DataFrame(rows,infer_schema_length=None)
df.write_csv(os.environ.get('OUT', '../../results/c5_rolls_by_agent_day.csv'))
print(df.height); print(df.group_by('evidence').len())
for r in df.filter(pl.col('evidence').is_in(['asserted','session'])).select('day','agent','priv_value','evidence','priv_id').iter_rows(): print(r)
