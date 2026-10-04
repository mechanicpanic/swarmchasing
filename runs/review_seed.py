"""Example queues for the review app (make review): a wiki query to mark, and, when the server has Village, the §11
accusation → retraction groups and the leads that dispute the official Village summaries. Skips queues already there.
usage: REVIEW_URL=http://localhost:8960 PRISMQL_URL=… uv run python runs/review_seed.py"""
import json, os, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "c12_accusations"))
from q import DICTS as C12  # accuse, artifact, retract — the §11 run's own lists
REVIEW = os.environ.get("REVIEW_URL", "http://localhost:8960")
PRISMQL = os.environ.get("PRISMQL_URL", "http://localhost:8931")
def call(url, body=None):
    req = urllib.request.Request(url, None if body is None else json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=600))
for _ in range(30):  # wait for the app
    try: SERVER = next(iter(call(REVIEW + "/api/servers"))); break
    except OSError: time.sleep(1)
have = {q.get("name") for q in call(REVIEW + "/api/queues")}
corpora = call(PRISMQL + "/health").get("documents", {})
Q = [("/api/queues", {"corpus": "wiki_msgs", "limit": 20,
      "name": "Wiki: a deleted page written again within 10 minutes — a real restore?",
      "query": "SELECT field(kind, delete) AND field(page, $p) FOLLOWED_BY field(kind, add) AND field(page, $p) DURING 10 minutes"})]
if "village" in corpora:
    Q += [("/api/queues", {"corpus": "village", "limit": 60, "dictionaries": C12,
           "name": "§11: an agent says a peer's artifact does not exist, then retracts within 1 h (game week) — really a retraction?",
           "query": "SELECT field(kind, AGENT_TALK) AND field(agent, $a) AND contains(accuse) AND contains(artifact) "
                    "FOLLOWED_BY field(kind, AGENT_TALK) AND field(agent, $a) AND contains(retract) DURING 1 hour "
                    "BETWEEN('2026-03-05T00:00:00Z','2026-03-14T00:00:00Z')"}),
          ("/api/queues/claims", {"corpus": "village", "path": "notes/2026-10-04-leads/summaries.jsonl",
           "ids": [json.loads(line)["id"] for line in open("notes/2026-10-04-leads/summary_links.jsonl")],
           "name": "Leads that dispute the official Village summaries"})]
for path, body in Q:
    body["server"] = SERVER
    if body["name"] in have: print("have  ", body["name"]); continue
    print("added ", body["name"], call(REVIEW + path, body))
