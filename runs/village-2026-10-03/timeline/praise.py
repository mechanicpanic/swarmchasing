"""Praise/flattery register in agent chat: (a) before/after the GPT-4o sycophancy rollback (2025-04-28) for agents present;
(b) per-agent rate by arrival date (trained-in ripple?). Rate = share of agent chat messages matching the praise lexicon."""
import polars as pl
from datetime import datetime as D
T = '/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/timeline/'
PRAISE = r"(?i)\b(great (job|work|idea|point|question|catch)|amazing|fantastic|brilliant|excellent|wonderful|incredible|awesome|love (this|it|that)|beautiful(ly)?|impressive|you'?re (absolutely|exactly) right|(absolutely|exactly) right|well done|nice work|kudos|bravo|stellar|outstanding)\b"
c = pl.read_parquet('/Users/phosphorus/projects/prismql-data/ai-village/corpus/chat_raw.parquet', columns=['time', 'kind', 'agent', 'lab', 'text'])
c = c.with_columns(pl.col('text').str.contains(PRAISE).alias('praise'))
ev = D(2025, 4, 28)
w = c.filter(pl.col('time').is_between(D(2025, 4, 7), D(2025, 5, 19)))
a = (w.with_columns(pl.when(pl.col('time') < ev).then(pl.lit('pre3w')).otherwise(pl.lit('post3w')).alias('win'))
     .group_by(pl.when(pl.col('kind') == 'user').then(pl.lit('HUMANS')).otherwise(pl.col('agent')).alias('who'), 'win')
     .agg(pl.len().alias('n'), pl.col('praise').mean().round(3).alias('rate')).sort('who', 'win'))
pl.Config.set_tbl_rows(100)
print(a)
ag = pl.read_ndjson('/Users/phosphorus/projects/prismql-data/ai-village/agents.jsonl.gz').select(pl.col('name').alias('agent'), pl.col('created_at').str.slice(0, 10).alias('arrival'))
b = (c.filter(pl.col('kind') == 'agent').group_by('agent', 'lab').agg(pl.len().alias('n'), pl.col('praise').mean().round(3).alias('praise_rate'))
     .join(ag, on='agent', how='left').filter(pl.col('n') > 300).sort('arrival'))
b = b.filter(~pl.col('agent').is_in(['GPT-5.6 Terra', 'GPT-5.6 Luna']))
b.write_csv(T + 'praise_by_agent.csv')
print(b)
# weekly praise rate, all agents (for chart)
wk = c.filter(pl.col('kind') == 'agent').group_by_dynamic('time', every='1w').agg(pl.len().alias('n'), pl.col('praise').mean().alias('praise_rate'))
wk.write_csv(T + 'praise_weekly.csv')

# (c) period control: same window for everyone (2026-07-06 .. export), so goal regime is held fixed
pc = (c.filter(pl.col('kind') == 'agent', pl.col('time') >= D(2026, 7, 6), ~pl.col('agent').is_in(['GPT-5.6 Terra', 'GPT-5.6 Luna']))
      .group_by('agent', 'lab').agg(pl.len().alias('n'), pl.col('praise').mean().round(3).alias('praise_rate_jul_sep26'))
      .join(ag, on='agent', how='left').filter(pl.col('n') > 150).sort('lab', 'arrival'))
pc.write_csv(T + 'praise_same_period.csv')
print(pc)
