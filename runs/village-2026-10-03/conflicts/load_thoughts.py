# Convert thoughts file 5 into a slim parquet (dedup on thought+event)
import polars as pl
src='/Users/phosphorus/projects/prismql-data/ai-village/village_embeddings_2026-09-29/5_village_thoughts_with_events.jsonl.gz'
df=pl.read_ndjson(src)
print(df.schema, df.height)
df=df.select('time','agent','of','event','thought','event_kind','event_text')
df.write_parquet('thoughts.parquet')
