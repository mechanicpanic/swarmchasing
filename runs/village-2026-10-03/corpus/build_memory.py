# Agent memories are full snapshots; turn each into a diff event against the
# same agent's previous snapshot: which lines entered memory, which dropped out.
import polars as pl
from pathlib import Path
D = Path(__file__).resolve().parent.parent
MAX = 4000  # chars of added/removed text kept per event

agents = pl.read_ndjson(D / "agents.jsonl.gz").select(pl.col("id").alias("agent_id"), pl.col("name").alias("agent"), pl.col("model_string").alias("model"))
m = (pl.read_ndjson(D / "agent_memories.jsonl.gz").join(agents, on="agent_id", how="left")
     .sort("agent_id", "created_at"))

def lines(s):
    return {l.strip() for l in (s or "").splitlines() if len(l.strip()) > 3}

rows = []
prev_agent, prev = None, set()
for id_, agent, model, t, content in m.select("id", "agent", "model", "created_at", "content").iter_rows():
    cur = lines(content)
    if agent != prev_agent:
        prev_agent, prev = agent, set()
    new = cur - prev
    added = [l for l in (content or "").splitlines() if l.strip() in new]
    removed = prev - cur
    if added or removed:
        rows.append(dict(id=id_, time=t, kind="memory", agent=agent, model=model, room="memory",
                         text="\n".join(added)[:MAX], dropped="\n".join(sorted(removed))[:MAX],
                         added_lines=len(added), dropped_lines=len(removed), snapshot_chars=len(content or "")))
    prev = cur

df = (pl.DataFrame(rows).with_columns(pl.col("time").str.to_datetime(time_unit="us")))
df.write_parquet(D / "corpus" / "memory_raw.parquet")
print(df.shape, "of", m.height, "snapshots")
print(df.select(pl.col("added_lines").median(), pl.col("dropped_lines").median(), pl.col("text").str.len_chars().mean()))
