# When an agent privately labels another agent's output with a harsh word, does the public message use it?
import re, polars as pl
from agents import names_in
S=pl.read_parquet('thought_friction_sents.parquet').filter(pl.col('event_kind')=='AGENT_TALK')
HARSH=re.compile(r"(?i)hallucinat|fabricat|suspicious|unreliable|lying|\blie[sd]?\b|false (claim|completion)|dropped the ball|keeps? (repeating|claiming|saying)|stuck in a loop|doubling down")
SOFT=re.compile(r"(?i)may have|might have|seems?|appears?|possibly|likely|perhaps|encountered an error|technical (issue|glitch)|sync|stale|cach|environment|divergen|visibility")
rows=[]
for r in S.iter_rows(named=True):
    m=HARSH.search(r['sent'])
    if not m: continue
    tg=[t for t in r['targets'] if t in names_in(r['event_text'] or '')]
    if not tg: continue
    pub=r['event_text']
    rows.append(dict(time=r['time'],agent=r['agent'],target=tg[0],word=m.group(0).lower(),sent=r['sent'].strip(),public=pub,
        same_harsh=bool(HARSH.search(pub)), softened=bool(SOFT.search(pub)),
        game=('2026-03-05'<=r['time']<'2026-03-17')))
E=pl.DataFrame(rows).unique(['agent','sent'])
E.write_parquet('euphemism.parquet')
print(E.height)
print(E.group_by('game').agg(pl.len(),pl.col('same_harsh').mean(),pl.col('softened').mean()))
print(E.filter(~pl.col('game')).with_columns(pl.col('word').str.slice(0,8)).group_by('word').agg(pl.len(),pl.col('same_harsh').mean()).sort('len',descending=True))
