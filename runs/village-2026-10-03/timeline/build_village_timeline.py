"""Build village_timeline.csv: village goals (spans), agent arrivals, agent departures (last chat), daily summaries (secondary)."""
import polars as pl, csv
D = '/Users/phosphorus/projects/prismql-data/ai-village/'
OUT = D + 'corpus/analysis/timeline/'
rows = []
g = pl.read_ndjson(D + 'village_goals.jsonl.gz').sort('start_time')
for r in g.iter_rows(named=True):
    rows.append(dict(date=r['start_time'][:10], end_date=(r['end_time'] or '')[:10], kind='village goal',
                     label=r['goal'].split('\n')[0][:140], detail=''))
a = pl.read_ndjson(D + 'agents.jsonl.gz')
chat = pl.read_parquet(D + 'corpus/chat_raw.parquet', columns=['time', 'kind', 'agent'])
span = chat.filter(pl.col('kind') == 'agent').group_by('agent').agg(pl.col('time').min().alias('first'), pl.col('time').max().alias('last'), pl.len().alias('n'))
a = a.join(span, left_on='name', right_on='agent', how='left')
for r in a.sort('created_at').iter_rows(named=True):
    rows.append(dict(date=r['created_at'][:10], end_date=str(r['last'])[:10] if r['last'] else '', kind='agent arrival',
                     label=r['name'], detail=f"model={r['model_string'][:40]}; chat_msgs={r['n']}; participating_at_export={r['is_participating']}"))
s = pl.read_ndjson(D + 'summaries.jsonl.gz').filter(pl.col('type') == 'daily')
s = s.with_columns(pl.coalesce('summary_date', pl.col('created_at').str.slice(0, 10)).alias('d'))
for r in s.sort('d').iter_rows(named=True):
    txt = (r['content'] or '').replace('\n', ' ')
    rows.append(dict(date=r['d'], end_date='', kind='daily summary', label=txt[:200], detail=f"generated_by={r['generated_by']}"))
rows.sort(key=lambda x: (x['date'], x['kind']))
with open(OUT + 'village_timeline.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['date', 'end_date', 'kind', 'label', 'detail']); w.writeheader(); w.writerows(rows)
print(len(rows), pl.DataFrame(rows).group_by('kind').len())
