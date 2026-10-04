#!/usr/bin/env python
"""Low-RAM grep over the village text stream (chat + thoughts + memory diffs).
Usage: uv run --project ~/projects/prismql python gv.py FROM TO REGEX [--src agent_chat,human_chat,thought,memory] [--agent SUBSTR] [--room SUBSTR] [--n 40] [--w 400]
FROM/TO: 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM' in UTC (summaries use PT = UTC-7/-8!).
REGEX: polars/Rust regex, case-insensitive applied automatically. Use '.' to match all.
Source: corpus/analysis/timeline/text_lean.parquet (cols time, src, agent, room, text).
Humans: src human_chat; never copy human names into leads.
"""
import sys, argparse, polars as pl
from datetime import datetime
p = argparse.ArgumentParser()
p.add_argument('frm'); p.add_argument('to'); p.add_argument('rx')
p.add_argument('--src', default='agent_chat,human_chat')
p.add_argument('--agent'); p.add_argument('--room')
p.add_argument('--n', type=int, default=40); p.add_argument('--w', type=int, default=400)
p.add_argument('--count', action='store_true', help='only print counts per agent/src')
a = p.parse_args()
def dt(s):
    return datetime.fromisoformat(s)
lf = pl.scan_parquet('/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/timeline/text_lean.parquet')
f = pl.col('time').is_between(dt(a.frm), dt(a.to)) & pl.col('src').is_in(a.src.split(','))
if a.rx != '.':
    f = f & pl.col('text').str.contains('(?i)' + a.rx)
if a.agent: f = f & pl.col('agent').fill_null('').str.contains('(?i)' + a.agent)
if a.room: f = f & pl.col('room').fill_null('').str.contains('(?i)' + a.room)
df = lf.filter(f).sort('time')
if a.count:
    print(df.group_by('src', 'agent').len().sort('len', descending=True).collect()); sys.exit()
df = df.head(a.n).collect()
for r in df.iter_rows(named=True):
    t = (r['text'] or '').replace('\n', ' ')[:a.w]
    print(f"{r['time']:%Y-%m-%d %H:%M:%S} [{r['src']}] {r['agent']} @{r['room']}: {t}")
print(f'-- {df.height} rows shown')
