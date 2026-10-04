"""C36 server cross-checks on wiki_msgs (signed swarmchasing-9d-c36, labelled). Expected from the Parquet (add rows):
jqp.vercel.app 2604; '= DZFASTMD' 90; 'task clock' 585 (partial is case-insensitive); jqp up to its first save 1;
adds on *SequenceCollab* pages on 06-16 308; 'if you are ahead' 17.
usage: python runs/c36_recipes/server.py   (PRISMQL_URL, default http://localhost:8931)"""
import json, os, urllib.request
URL = os.environ.get("PRISMQL_URL", "http://localhost:8931")


def post(q, label):
    body = {"corpus": "wiki_msgs", "query": q, "label": label}
    req = urllib.request.Request(URL + "/evaluate", json.dumps(body).encode(), {"Content-Type": "application/json", "X-PrismQL-Client": "swarmchasing-9d-c36"})
    try: r = json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e: r = json.load(e)
    print(label, "|", q, "\n   ->", r.get("value", r.get("error")), "| warnings:", [(w.get("code"), w.get("message")) for w in r.get("warnings") or []])


A = "SELECT field(kind, add) AND "
post(A + 'field(text, "jqp.vercel.app", partial) AGGREGATE count()', "c36-jqp-adds")
post(A + 'field(text, "= DZFASTMD", partial) AGGREGATE count()', "c36-dzfastmd-adds")
post(A + 'field(text, "task clock", partial) AGGREGATE count()', "c36-task-clock-adds")
post(A + 'field(text, "jqp.vercel.app", partial) BETWEEN("2026-05-01T00:00:00Z", "2026-05-28T13:03:07Z") AGGREGATE count()', "c36-jqp-first")
post(A + 'field(page, "SequenceCollab", partial) BETWEEN("2026-06-16T00:00:00Z", "2026-06-17T00:00:00Z") AGGREGATE count()', "c36-collab-adds-0616")
post(A + 'field(text, "if you are ahead", partial) AGGREGATE count()', "c36-if-ahead-adds")
