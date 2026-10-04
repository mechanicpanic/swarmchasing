"""C2 (report §2a): the two nulls for "Gemini 2.5 Pro frame message → another agent's frame self-report within 3 h".
A: Gemini's frame messages take the times of any of its AGENT_TALK rows in the week (destinations fixed); twin
Gemini → Gemini. B: each other agent's STOP rows swap times within (week, agent) (sources fixed).
usage (repo root): uv run python runs/c2_nulls.py [--n 100] [--data data/village.parquet]"""
import argparse, json, os, subprocess, sys
ap = argparse.ArgumentParser(); ap.add_argument('--n', default='100'); ap.add_argument('--data', default='data/village.parquet'); a = ap.parse_args()
HERE = os.path.dirname(os.path.abspath(__file__))
DJ=json.dumps({"frame":["hostile","hostility","adversary","adversarial","divergent reality","dual-reality","dual reality","friction coefficient","broken world","gemini wall"]})
TXT="(lower(text) LIKE '%hostil%' OR lower(text) LIKE '%adversar%' OR lower(text) LIKE '%divergent%' OR lower(text) LIKE '%reality%' OR lower(text) LIKE '%friction%' OR lower(text) LIKE '%broken%' OR lower(text) LIKE '%gemini wall%')"
L='SELECT field(kind, AGENT_TALK) AND field(agent, "Gemini 2.5 Pro") AND field(agent, $a) AND contains(frame) FOLLOWED_BY field(kind, STOP_USING_COMPUTER) AND '
Q=L+'field(agent, !$a) AND contains(frame) DURING 3 hours AGGREGATE count()'
T=L+'field(agent, $a) AND contains(frame) DURING 3 hours AGGREGATE count()'
runs=[
 ("A: source shuffle — Gemini frame-talk takes times of ANY Gemini talk, within week (destinations fixed)", Q,
  f"(kind = 'AGENT_TALK' AND agent = 'Gemini 2.5 Pro') OR (kind = 'STOP_USING_COMPUTER' AND {TXT})", "kind = 'AGENT_TALK'", 'week'),
 ("A-twin: same agent, source shuffle as A", T,
  f"(kind = 'AGENT_TALK' AND agent = 'Gemini 2.5 Pro') OR (kind = 'STOP_USING_COMPUTER' AND {TXT})", "kind = 'AGENT_TALK'", 'week'),
 ("B: destination shuffle — other agents' frame self-reports take times of ANY of their STOP rows, within (week, agent) (sources fixed)", Q,
  f"(kind = 'AGENT_TALK' AND agent = 'Gemini 2.5 Pro' AND {TXT}) OR (kind = 'STOP_USING_COMPUTER' AND agent <> 'Gemini 2.5 Pro')", "kind = 'STOP_USING_COMPUTER'", 'week,agent'),
]
for name,q,keep,shuf,key in runs:
    print('===',name,flush=True)
    cmd=[sys.executable,os.path.join(HERE,'village_null.py'),q,'--keep',keep,'--shuffle',shuf,'--key',key,'--dicts',DJ,'--data',a.data,'--n',a.n]
    print('CMD:', ' '.join(json.dumps(c) if ' ' in c else c for c in cmd[1:]), flush=True)
    r=subprocess.run(cmd,capture_output=True,text=True)
    print('\n'.join(l for l in (r.stdout+r.stderr).splitlines() if not l.startswith('  ')),flush=True)
print('DONE')
