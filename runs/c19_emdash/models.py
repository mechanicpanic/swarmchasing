"""C19 side check: did an agent's served model change under the same name?

One pass over the raw events export: for every agent action that carries a raw
model `output`, collect any `"model": "..."` strings it reports, per agent and
month. Anthropic responses carry the served model; most other providers' raw
outputs do not, so an empty cell means "not recorded", not "unchanged".

usage: REPO=... OUT=... python runs/c19_emdash/models.py
"""

import gzip
import json
import os
import re
from collections import Counter, defaultdict

REPO = os.environ.get("REPO", ".")
OUT = os.environ.get("OUT", "results/c19")
EV = f"{REPO}/data/village/events.jsonl.gz"
AG = f"{REPO}/data/village/agents.jsonl.gz"
MODEL = re.compile(r'"model"\s*:\s*"([^"]{2,80})"')

names = {}
with gzip.open(AG, "rt") as f:
    for line in f:
        a = json.loads(line)
        names[a["id"]] = a["name"]

seen = defaultdict(Counter)  # (agent, month) -> model string counts
rows = defaultdict(int)  # (agent, month) -> events with an output
with gzip.open(EV, "rt") as f:
    for line in f:
        e = json.loads(line)
        d = e.get("data") or {}
        out = d.get("output")
        if out is None:
            continue
        who = names.get(d.get("speakerId") or d.get("agentId"), "?")
        month = (e.get("created_at") or "")[:7]
        rows[(who, month)] += 1
        for m in MODEL.findall(json.dumps(out)):
            seen[(who, month)][m] += 1

os.makedirs(OUT, exist_ok=True)
with open(f"{OUT}/models_by_month.jsonl", "w") as f:
    for k in sorted(rows):
        f.write(
            json.dumps(
                {
                    "agent": k[0],
                    "month": k[1],
                    "events_with_output": rows[k],
                    "models": dict(seen[k]),
                }
            )
            + "\n"
        )
print(f"wrote {OUT}/models_by_month.jsonl ({len(rows)} agent-months)")
