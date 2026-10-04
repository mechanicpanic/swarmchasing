"""C8 helper: candidate external targets for hand-labelling. For each (agent, outside domain) named in the agent's own
STOP_USING_COMPUTER summaries or AGENT_TALK in the window, print the first rows that name it with a snippet around
the domain. Output is for reading, not a finding; the labels go to targets.csv by hand.
usage (repo root): REPO=. python runs/c8_chaotic_swarm/candidates.py [--start 2025-11-19T17:59] [--end 2025-11-20T22:02]"""
import argparse
import polars as pl
from common import load_village, outside_domains, window

ap = argparse.ArgumentParser()
ap.add_argument("--start", default="2025-11-19T17:59")
ap.add_argument("--end", default="2025-11-20T22:02")
a = ap.parse_args()
d = window(load_village(), a.start, a.end).filter(pl.col("kind").is_in(["STOP_USING_COMPUTER", "AGENT_TALK"]))
seen = {}
for r in d.sort("time").iter_rows(named=True):
    for dom, pos in outside_domains(r["text"]):
        k = (r["agent"], dom)
        seen.setdefault(k, [])
        if len(seen[k]) < 3:
            t = r["text"]
            seen[k].append(f"    {r['time']:%m-%d %H:%M} {r['id'][:8]} {r['kind'][:4]} …{t[max(0, pos - 220):pos + 160]!r}")
for (ag, dom), rows in sorted(seen.items()):
    print(f"## {ag} | {dom}")
    print("\n".join(rows))
