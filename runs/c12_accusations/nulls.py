"""C12 (report §11): time-shuffle nulls for accusation → retraction and its twin (accusation → any message), per
window. Every AGENT_TALK row in the window is kept; each agent's message times are permuted within (agent, day), so
the set of times an agent spoke (its bursts) stays and only which message sits where moves.
usage (repo root): uv run python runs/c12_accusations/nulls.py [--n 200] [--data data/village.parquet]"""
import argparse, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
from q import DICTS as D  # in-band dictionaries: accuse, artifact, retract

ap = argparse.ArgumentParser(); ap.add_argument('--n', default='200'); ap.add_argument('--data', default='data/village.parquet')
a = ap.parse_args()
ACC = "field(kind, AGENT_TALK) AND field(agent, $a) AND contains(accuse) AND contains(artifact)"
Q = {'acc_ret': f"SELECT {ACC} FOLLOWED_BY field(kind, AGENT_TALK) AND field(agent, $a) AND contains(retract) DURING 1 hour AGGREGATE count()",
     'acc_any': f"SELECT {ACC} FOLLOWED_BY field(kind, AGENT_TALK) AND field(agent, $a) DURING 1 hour AGGREGATE count()"}
W = {'game': ("2026-03-05", "2026-03-14", ""),
     'game_without_0312': ("2026-03-05", "2026-03-14", " AND CAST(time AS DATE) <> CAST('2026-03-12' AS DATE)"),
     'before': ("2026-02-05", "2026-03-05", ""), 'after': ("2026-03-14", "2026-04-11", "")}
here = os.path.dirname(os.path.abspath(__file__))
for w, (lo, hi, extra) in W.items():
    keep = f"kind = 'AGENT_TALK' AND CAST(time AS DATE) >= CAST('{lo}' AS DATE) AND CAST(time AS DATE) < CAST('{hi}' AS DATE){extra}"
    for k, q in Q.items():
        cmd = [sys.executable, os.path.join(here, '..', 'village_null.py'), q, '--keep', keep, '--shuffle', 'true',
               '--key', 'agent,day', '--n', a.n, '--data', a.data, '--dicts', json.dumps(D)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(f'=== {w} {k}  keep: {keep}'); print('\n'.join(l for l in (r.stdout + r.stderr).splitlines() if not l.startswith('  ')), flush=True)
