"""C8 server cross-checks on village (signed swarmchasing-9d-c8, labelled). Observed 2026-10-04: 927 rows for the phrase
(c8.py's literal "chaotic swarm" gives 901; the 26 extra are "chaotic-swarm-*" file names on 2026-01-09, the server
splits the hyphen), 501 in the Substack goal (c8.py: 501), AGENT_TALK by agent in the goal 102/13/9/9/6/2 (= c8.py),
97 "external nodes" rows on Days 232-233, 7 Haiku "pending moderation" rows, 15 organiser messages in the goal.
usage: python runs/c8_chaotic_swarm/server.py   (PRISMQL_URL, default http://localhost:8931)"""
import json, os, urllib.request
URL = os.environ.get("PRISMQL_URL", "http://localhost:8931")
GOAL = 'BETWEEN("2025-11-17T16:03:14Z", "2025-12-01T14:20:16Z")'
DAYS = 'BETWEEN("2025-11-19T17:59:00Z", "2025-11-20T22:02:00Z")'


def post(q, label):
    body = {"corpus": "village", "query": q, "label": label}
    req = urllib.request.Request(URL + "/evaluate", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "X-PrismQL-Client": "swarmchasing-9d-c8"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        r = json.load(e)
    v = r.get("value", r.get("grouped_values", r.get("error")))
    print(label, "|", q, "\n   ->", json.dumps(v)[:900], "| warnings:",
          [(w.get("code"), w.get("message")) for w in r.get("warnings") or []])


post('SELECT contains_phrase("chaotic swarm") AGGREGATE count()', "c8-cs-all")
post(f'SELECT contains_phrase("chaotic swarm") {GOAL} AGGREGATE count()', "c8-cs-substack-goal")
post('SELECT contains_phrase("chaotic swarm") GROUP BY DAYS(time) AGGREGATE count()', "c8-cs-by-day")
post(f'SELECT contains_phrase("chaotic swarm") AND field(kind, AGENT_TALK) {GOAL} GROUP BY agent AGGREGATE count()',
     "c8-cs-talk-by-agent-goal")
post(f'SELECT contains_phrase("external nodes") {DAYS} AGGREGATE count()', "c8-external-nodes-days232-233")
post(f'SELECT contains_phrase("pending moderation") AND field(agent, "Claude Haiku 4.5") {DAYS} AGGREGATE count()',
     "c8-haiku-pending-moderation")
post(f'SELECT field(kind, USER_TALK) AND NOT field(agent, automated) {GOAL} AGGREGATE count()', "c8-human-talk-goal")
