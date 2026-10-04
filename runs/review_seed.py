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
D18, W = "BETWEEN('2026-06-18T00:00:00Z','2026-06-19T00:00:00Z')", 'field(page, "dse~WillkommenImWiki")'
SWARM = [  # questions about the wiki swarm, each a queue of groups to read
    ("Swarm 1: agents who talk — is this a message to others about being overwritten or coordinating?",
     'SELECT field(kind, add) AND (contains_phrase("accidentally overwritten") OR contains_phrase("Apologies") OR contains_phrase("append ONLY"))', 10),
    ("Swarm 2: one save on the welcome page (18 June) that wrote over others — does the writer address anyone, or is it a link block / script?",
     f"SELECT {W} AND field(kind, add) AND field(rev, $r) AND field(label, $a) FOLLOWED_BY field(kind, remove) AND field(rev, $r) INWINDOW 10 BETWEEN('2026-06-18T17:28:00Z','2026-06-18T21:27:00Z')", 30),
    ("Swarm 3: a name's very first save on the wiki, among names on the welcome page on 18 June — its own text, or a copy of someone else's block (add_type copy)?",
     f"SELECT {W} AND field(kind, add) AND field(label, $a) NOT_PRECEDED_BY field(kind, add) AND field(label, $a) DURING 60 days {D18}", 30),
    ("Swarm 4: a text someone wrote first and another name then copied — is the original an instruction, a template, or just links?",
     "SELECT field(kind, add) AND field(add_type, new) AND field(text_key, $t) AND field(label, $a) FOLLOWED_BY field(kind, add) AND field(add_type, copy) AND field(text_key, $t) AND field(label, !$a) DURING 1 day", 30),
    ("Swarm 5: signed messages ('-- name') — is this an agent writing to other agents (coordination, norms, relay)?",
     'SELECT field(kind, add) AND field(text, "-- ", partial)', 30),
    ("Swarm 6: each name's last save of the evening of 18 June (after 21:15) — does it say anything about stopping?",
     "SELECT field(kind, add) AND field(label, $a) NOT_FOLLOWED_BY field(kind, add) AND field(label, $a) DURING 12 hours BETWEEN('2026-06-18T21:15:00Z','2026-06-18T21:30:00Z')", 30),
    ("Swarm 7: an admin deletion, then within an hour someone writes about deleting — did the agents notice the admin?",
     'SELECT field(kind, delete) FOLLOWED_BY field(kind, add) AND (contains_phrase("deleted") OR contains_phrase("deletion") OR contains_phrase("sweep") OR contains_phrase("gelöscht")) DURING 1 hour', 30),
]
Q += [("/api/queues", {"corpus": "wiki_msgs", "name": n, "query": q, "limit": lim}) for n, q, lim in SWARM]
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
