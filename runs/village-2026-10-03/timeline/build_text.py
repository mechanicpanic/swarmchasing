"""Lean text table for keyword scans: chat (agent/user), THOUGHT rows (deduped on text), memory diffs.
Writes timeline/text_lean.parquet (time, src, agent, text)."""
import polars as pl
D = '/Users/phosphorus/projects/prismql-data/ai-village/'
chat = pl.scan_parquet(D + 'corpus/chat_raw.parquet').select(
    pl.col('time'), pl.when(pl.col('kind') == 'user').then(pl.lit('human_chat')).otherwise(pl.lit('agent_chat')).alias('src'),
    'agent', 'room', 'text')
th = (pl.scan_parquet(D + 'village_embeddings_2026-09-29/3_village_full_with_text.parquet')
      .filter(pl.col('kind') == 'THOUGHT')
      .select(pl.col('time').dt.replace_time_zone(None), pl.lit('thought').alias('src'), 'agent', 'room', 'text')
      .unique(subset=['agent', 'text'], keep='first'))
mem = (pl.scan_parquet(D + 'corpus/village_raw.parquet').filter(pl.col('kind') == 'memory')
       .select('time', pl.lit('memory').alias('src'), 'agent', pl.lit(None, pl.String).alias('room'), 'text'))
out = pl.concat([chat, th, mem], how='vertical_relaxed').filter(pl.col('text').is_not_null())
out.sink_parquet(D + 'corpus/analysis/timeline/text_lean.parquet')
t = pl.read_parquet(D + 'corpus/analysis/timeline/text_lean.parquet', columns=['src'])
print(t.group_by('src').len())
