# Chat + memory-diff events in one time-ordered stream.
import polars as pl
from pathlib import Path
C = Path(__file__).resolve().parent
chat = pl.read_parquet(C / "chat_raw.parquet").with_columns(pl.lit(None, pl.Utf8).alias("dropped"), pl.lit(None, pl.Int64).alias("added_lines"), pl.lit(None, pl.Int64).alias("dropped_lines"))
mem = pl.read_parquet(C / "memory_raw.parquet").select(chat.columns)
df = pl.concat([chat, mem.cast(chat.schema)]).sort("time")
df.write_parquet(C / "village_raw.parquet")
print(df.shape); print(df.group_by("kind").len())
