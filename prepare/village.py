"""AI Village export → one event table for `prismql ingest table`.

Dataset knowledge lives here and nowhere else: which export table is the
stream (`events`, ordered by `event_index`), which lookup tables hang off it
(`agents` for names), and which payload fields become columns. Output:
data/village_events.parquet; then the Makefile runs `prismql ingest table`
on it (sort, position, time, emb).
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import polars as pl

SRC = Path("data/village")
DST = Path("data/village_events.parquet")

TEXT_FIELDS = ("content", "sessionGoal", "summary", "nextSessionGoal", "query")


def agent_names() -> dict[str, str]:
    with gzip.open(SRC / "agents.jsonl.gz", "rt", encoding="utf-8") as fh:
        rows = (json.loads(line) for line in fh if line.strip())
        return {r["id"]: r["name"] for r in rows}


def main() -> None:
    names = agent_names()
    out: list[dict] = []
    with gzip.open(SRC / "events.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            d = rec.get("data") or {}
            agent_id = d.get("speakerId") or d.get("agentId")
            text = next((d[f] for f in TEXT_FIELDS if d.get(f)), None)
            out.append(
                {
                    "id": rec["id"],
                    "event_index": rec["event_index"],
                    "created_at": rec["created_at"],
                    "kind": d.get("actionType"),
                    "agent": names.get(agent_id) or d.get("speakerName"),
                    "agent_id": agent_id,
                    "room": d.get("roomId"),
                    "message_id": d.get("messageId"),
                    "cu_session": d.get("computerUseSessionId"),
                    "text": text,
                    "answer": d.get("answerToQuery"),
                    "seconds": d.get("seconds"),
                    "cost": d.get("cost"),
                    "input_tokens": d.get("inputTokens"),
                    "output_tokens": d.get("outputTokens"),
                }
            )
    df = pl.DataFrame(out, infer_schema_length=None)
    df.write_parquet(DST)
    print(f"{DST}: {df.height} rows; kinds: {df.get_column('kind').n_unique()}; "
          f"agents: {df.get_column('agent').n_unique()}")


if __name__ == "__main__":
    main()
