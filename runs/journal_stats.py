"""How many queries the agents and people sent the server during the hackathon, from the shipped journal.
usage: uv run python runs/journal_stats.py [--since 2026-10-03] [--until 2026-10-05] [--journal logs/server-journal.jsonl]
Clients are classed by the name they signed with (X-PrismQL-Client): agents sign with their session or role name,
the board signs `board`, scripted checks `smoke`/`seed`/`probe`; unsigned requests show as an address."""
import argparse, collections, json

ap = argparse.ArgumentParser()
ap.add_argument("--since", default="2026-10-03"); ap.add_argument("--until", default="2026-10-05")
ap.add_argument("--journal", default="logs/server-journal.jsonl")
a = ap.parse_args()

# agents that rebuilt or replayed finished findings for the demo (figures, replays, README checks), not investigating
PACKAGING = {"claude-village-findings", "claude-cheatsheet-port", "claude-figures", "swarmchasing-findings", "cheatsheet",
             "claude-readme", "claude-pin-check", "readme-test"}

def klass(who: str) -> str:
    if who in PACKAGING: return "agents, packaging the demo"
    if who == "board": return "people, from the board"
    if who.split("-")[0] in ("smoke", "seed", "probe"): return "scripted checks"
    if who[:1].isdigit(): return "unsigned"
    return "agents"

rows = [json.loads(line) for line in open(a.journal, encoding="utf-8")]
rows = [r for r in rows if a.since <= r["ts"][:10] < a.until]
by = collections.Counter((klass(r.get("who", "")), r.get("kind", "?")) for r in rows)
who = collections.Counter(r.get("who", "") for r in rows if klass(r.get("who", "")) == "agents")
print(f"{len(rows)} requests, {rows[0]['ts'][:16]} → {rows[-1]['ts'][:16]} UTC\n")
print("| who | evaluate | search | similar | all |\n|---|---|---|---|---|")
for k in ("agents", "agents, packaging the demo", "people, from the board", "scripted checks", "unsigned"):
    n = {kind: by[(k, kind)] for kind in ("evaluate", "search", "similar")}
    tot = sum(v for (kk, _), v in by.items() if kk == k)
    if tot: print(f"| {k} | {n['evaluate']} | {n['search']} | {n['similar']} | {tot} |")
print(f"\n{len(who)} investigating agent names; the busiest: " + ", ".join(f"{w} {n}" for w, n in who.most_common(5)))
