"""AI Village export → one event table for `prismql ingest table`.

Dataset knowledge lives here and nowhere else: which export table is the
stream (`events`, ordered by `event_index`), which lookup tables hang off it
(`agents` for names), and which payload fields become columns. Output:
data/village_events.parquet; then the Makefile runs `prismql ingest table`
on it (sort, position, time, emb).

Reasoning: the model's thinking at each event (Anthropic `thinking` blocks,
OpenAI reasoning summaries, Gemini thought parts, GLM/DeepSeek `reasoning`)
lives in the provider-shaped `data.output`; `village-transcript.json` already
flattens all shapes into one `thinking` string per event. Each such thought
becomes its own row, kind THOUGHT, placed immediately before the event it led
to (`of` = that event's kind, `event` = its id), so "thought X, then did Y" is
a plain FOLLOWED_BY and one `emb` covers what was said and what was thought.
Order key: `seq` = 2*event_index (+1 for the event itself).
Caveat for comparisons: OpenAI and Gemini expose summaries, Anthropic older
models raw thinking, newer ones summarised — lengths and wording are not
comparable across providers.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import polars as pl

SRC = Path("data/village")
DST = Path("data/village_events.parquet")

TEXT_FIELDS = ("content", "sessionGoal", "summary", "nextSessionGoal", "query")
TRANSCRIPT = SRC / "village-transcript.json"


def thoughts() -> dict[tuple[str, str, str], str]:
    """(timestamp to the millisecond, actionType, agent name) -> thinking."""
    with open(TRANSCRIPT, encoding="utf-8") as fh:
        t = json.load(fh)
    out: dict[tuple[str, str, str], str] = {}
    for day in t["days"]:
        for e in day["events"]:
            th = e.get("thinking")
            if th and th.strip():
                who = e.get("agentName") or e.get("speakerName")
                out[(e["timestamp"][:23], e["type"], who)] = th
    return out


def ms_key(created_at: str) -> str:
    """`2025-12-29 18:49:21.291984` -> `2025-12-29T18:49:21.291`, the transcript's key."""
    date, clock = created_at.split(" ")
    hms, _, frac = clock.partition(".")
    return f"{date}T{hms}.{(frac + '000')[:3]}"


def agent_names() -> dict[str, str]:
    with gzip.open(SRC / "agents.jsonl.gz", "rt", encoding="utf-8") as fh:
        rows = (json.loads(line) for line in fh if line.strip())
        return {r["id"]: r["name"] for r in rows}


def main() -> None:
    names = agent_names()
    thought = thoughts()
    out: list[dict] = []
    with gzip.open(SRC / "events.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            d = rec.get("data") or {}
            agent_id = d.get("speakerId") or d.get("agentId")
            text = next((d[f] for f in TEXT_FIELDS if d.get(f)), None)
            agent = names.get(agent_id) or d.get("speakerName")
            th = thought.get((ms_key(rec["created_at"]), d.get("actionType"), agent))
            if th:
                out.append(
                    {
                        "id": rec["id"] + ":thought",
                        "seq": 2 * rec["event_index"],
                        "event_index": rec["event_index"],
                        "created_at": rec["created_at"],
                        "kind": "THOUGHT",
                        "of": d.get("actionType"),
                        "event": rec["id"],
                        "agent": agent,
                        "agent_id": agent_id,
                        "room": d.get("roomId"),
                        "cu_session": d.get("computerUseSessionId"),
                        "text": th,
                    }
                )
            out.append(
                {
                    "id": rec["id"],
                    "seq": 2 * rec["event_index"] + 1,
                    "event_index": rec["event_index"],
                    "created_at": rec["created_at"],
                    "kind": d.get("actionType"),
                    "agent": agent,
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
    n_th = df.filter(pl.col("kind") == "THOUGHT").height
    print(f"thoughts attached: {n_th} of {len(thought)} in the transcript")
    print(
        f"{DST}: {df.height} rows; kinds: {df.get_column('kind').n_unique()}; "
        f"agents: {df.get_column('agent').n_unique()}"
    )


if __name__ == "__main__":
    main()
