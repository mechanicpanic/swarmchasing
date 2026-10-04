# Flatten AI Village chat into one event table: speaker name, room, goal era.
import polars as pl
from pathlib import Path
D = Path(__file__).resolve().parent.parent
agents = pl.read_ndjson(D / "agents.jsonl.gz").select(pl.col("id").alias("agent_speaker_id"), pl.col("name").alias("agent"), pl.col("model_string").alias("model"))
rooms = pl.read_ndjson(D / "chat_rooms.jsonl.gz").select(pl.col("id").alias("room_id"), pl.col("name").alias("room"))
msgs = pl.read_ndjson(D / "chat_messages.jsonl.gz", infer_schema_length=None)
df = (msgs.join(agents, on="agent_speaker_id", how="left").join(rooms, on="room_id", how="left")
      .with_columns(pl.when(pl.col("speaker_type") == "user").then(pl.lit("human")).otherwise(pl.col("agent")).alias("agent"),
                    pl.col("speaker_type").alias("kind"),
                    pl.col("content").alias("text"),
                    pl.col("created_at").str.to_datetime(time_unit="us").alias("time"))
      .with_columns(pl.col("room").fill_null("main"), pl.col("model").fill_null("human"))
      .sort("time")
      .select("id", "time", "kind", "agent", "model", "room", "text"))
df.write_parquet(D / "corpus" / "chat_raw.parquet")
print(df.shape); print(df.group_by("agent").len().sort("len", descending=True).head(40))
