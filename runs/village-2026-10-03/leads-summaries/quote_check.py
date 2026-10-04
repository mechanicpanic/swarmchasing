# Check whether quotes in LLM-written summaries exist verbatim in the chat (agent_chat).
import re, polars as pl, sys
d=pl.read_ndjson('/Users/phosphorus/projects/prismql-data/ai-village/summaries.jsonl.gz').filter(pl.col('type').is_in(['agent','daily','goal']))
d=d.with_columns(pl.col('content').str.len_chars().alias('n')).sort('n',descending=True)
d=pl.concat([d.filter(pl.col('type')=='daily').unique('summary_date',keep='first'), d.filter(pl.col('type')!='daily')])
rx=re.compile(r'<quote>\s*([^:<]{2,40}):\s*"?(.+?)"?\s*\[(\d{4}-\d\d-\d\d) [\d:]+ PT\]\s*</quote>', re.S)
Q=[]
for r in d.iter_rows(named=True):
    for m in rx.finditer(r['content']):
        sp,txt,day=m.group(1).strip(),m.group(2).strip(),m.group(3)
        Q.append(dict(type=r['type'],target=r['summary_target'],speaker=sp,day=day,q=txt))
print('quotes',len(Q), file=sys.stderr)
chat=pl.scan_parquet('/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/timeline/text_lean.parquet').filter(pl.col('src').is_in(['agent_chat','human_chat'])).select('time','agent','text').collect()
chat=chat.with_columns(pl.col('time').dt.date().cast(pl.Utf8).alias('d'), pl.col('text').str.replace_all(r'[‘’]',"'").str.replace_all(r'[“”]','"').str.replace_all('\u2011','-').str.replace_all(r'[^A-Za-z0-9 ]','').str.replace_all(r'\s+',' ').alias('t'))
out=[]
for q in Q:
    # normalise: take a 30-char probe from middle, strip ellipses and markdown
    s=q['q'].replace('’',"'").replace('‘',"'").replace('“','"').replace('”','"').replace('**','')
    parts=[p.strip() for p in re.split(r'\.\.\.|…|\[\.\.\.\]',s) if len(p.strip())>=25]
    probe=(parts[0] if parts else s)
    probe=re.sub(r'\s+',' ',re.sub(r'[^A-Za-z0-9 ]','',probe)).strip()[:30]
    from datetime import date,timedelta
    dd=date.fromisoformat(q['day']); win=[str(dd+timedelta(days=k)) for k in (-1,0,1)]
    sub=chat.filter(pl.col('d').is_in(win))
    hit=sub.filter(pl.col('t').str.replace_all(r'\*\*','').str.contains(probe,literal=True))
    any_day=None
    if hit.height==0:
        any_day=chat.filter(pl.col('t').str.replace_all(r'\*\*','').str.contains(probe,literal=True)).height
    out.append({**q,'probe':probe,'found_near_date':hit.height>0,'found_anywhere':any_day})
pl.DataFrame(out).write_parquet('quote_check.parquet')
o=pl.DataFrame(out)
print(o.group_by('type').agg(pl.len(),pl.col('found_near_date').mean().alias('near'),(pl.col('found_near_date')|(pl.col('found_anywhere').fill_null(0)>0)).mean().alias('anywhere')))
