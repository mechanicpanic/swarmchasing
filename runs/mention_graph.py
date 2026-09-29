"""Who addresses whom in agent chat: '@<agent name>' mentions in AGENT_TALK, per village goal period.
in = times addressed; req = addressed with a request (could you / can you / please / ?); out = mentions made;
reply30 = share of requests the addressee answers in chat within 30 minutes. Writes results/mention_graph.parquet."""
import gzip, json, re, polars as pl
names = sorted({json.loads(l)['name'] for l in gzip.open('data/village/agents.jsonl.gz','rt')}, key=len, reverse=True)
pat = re.compile(r'@(' + '|'.join(re.escape(n) for n in names) + r')(?![\w.])', re.I)
canon = {n.lower(): n for n in names}
goals = sorted(([json.loads(l) for l in gzip.open('data/village/village_goals.jsonl.gz','rt')]), key=lambda r: r.get('start_time') or r['created_at'])
t = pl.read_parquet('data/village.parquet', columns=['time','kind','agent','text']).filter(pl.col('kind')=='AGENT_TALK').sort('time')
rows = []
for tm, ag, tx in t.select('time','agent','text').iter_rows():
    for m in {canon[x.lower()] for x in pat.findall(tx or '')} - {ag}:
        rows.append((tm, ag, m, bool(re.search(r'could you|can you|please|\?', tx, re.I))))
e = pl.DataFrame(rows, schema=['time','src','dst','request'], orient='row')
starts = pl.DataFrame({'gstart': [pl.Series([(g.get('start_time') or g['created_at'])]).str.to_datetime(time_zone='UTC')[0] for g in goals], 'goal': [g['goal'][:60] for g in goals]}).sort('gstart')
e = e.sort('time').join_asof(starts, left_on='time', right_on='gstart')
# reply within 30 min: next talk by dst after the request
talk = t.select(pl.col('time').alias('rt'), pl.col('agent').alias('dst')).sort('rt')
req = e.filter('request').sort('time').join_asof(talk, left_on='time', right_on='rt', by='dst', strategy='forward')
req = req.with_columns(((pl.col('rt') - pl.col('time')).dt.total_minutes() <= 30).fill_null(False).alias('reply30'))
e.write_parquet('results/mention_graph.parquet')
print('mention edges:', e.height, '| with request:', e['request'].sum())
def week(lo, hi, title):
    w = e.filter((pl.col('time') >= pl.lit(lo).str.to_datetime(time_zone='UTC')) & (pl.col('time') < pl.lit(hi).str.to_datetime(time_zone='UTC')))
    r = req.filter((pl.col('time') >= pl.lit(lo).str.to_datetime(time_zone='UTC')) & (pl.col('time') < pl.lit(hi).str.to_datetime(time_zone='UTC')))
    tab = (w.group_by('dst').agg(pl.len().alias('in'), pl.col('request').sum().alias('req_in')).rename({'dst':'agent'})
           .join(w.group_by('src').agg(pl.len().alias('out'), pl.col('request').sum().alias('req_out')).rename({'src':'agent'}), on='agent', how='full', coalesce=True)
           .join(r.group_by('dst').agg(pl.col('reply30').mean().round(2).alias('reply30')).rename({'dst':'agent'}), on='agent', how='left')
           .fill_null(0).with_columns((pl.col('in') / pl.col('in').sum()).round(2).alias('in_share')).sort('in', descending=True))
    print(f'\n## {title}  ({lo} → {hi}), {w.height} mentions'); print(tab.head(6))
with pl.Config(tbl_width_chars=160, tbl_rows=8):
    week('2026-01-05', '2026-01-12', 'Elect a village leader; the leader chooses the goal')
    week('2026-06-01', '2026-06-08', 'Follow your leader!')
    week('2026-03-05', '2026-03-16', 'Develop a turn-based RPG together (no appointed leader)')
    week('2025-09-08', '2025-09-22', 'Human subjects experiment (no appointed leader)')
