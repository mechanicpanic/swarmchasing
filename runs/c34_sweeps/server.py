"""C34 server cross-checks on wiki_msgs (signed swarmchasing-9d-c34, labelled): sweeps, deletes before the last full
24 h window, and deletes followed by an add on the same page. Expected: 108, 7, 420, 24, 52 (matches c34.py / episodes.py).
usage: python runs/c34_sweeps/server.py   (PRISMQL_URL, default http://localhost:8931)"""
import json, os, urllib.request
URL = os.environ.get("PRISMQL_URL", "http://localhost:8931")
def post(q, label):
    body = {"corpus": "wiki_msgs", "query": q, "label": label}
    req = urllib.request.Request(URL + "/evaluate", json.dumps(body).encode(), {"Content-Type": "application/json", "X-PrismQL-Client": "swarmchasing-9d-c34"})
    try: r = json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e: r = json.load(e)
    print(label, "|", q, "\n   ->", r.get("value", r.get("error")), "| warnings:", [(w.get("code"), w.get("message")) for w in r.get("warnings") or []])
post("SELECT RUN(field(kind, delete)){10,400} DURING 10 minutes AGGREGATE count()", "c34-sweeps-all")
post('SELECT RUN(field(kind, delete)){10,400} DURING 10 minutes BETWEEN("2026-06-18T00:00:00Z", "2026-06-21T09:20:05Z") AGGREGATE count()', "c34-sweeps-active")
post('SELECT field(kind, delete) BETWEEN("2026-06-18T00:00:00Z", "2026-06-21T09:20:05Z") AGGREGATE count()', "c34-deletes-active")
post('SELECT field(kind, delete) AND field(page, $p) FOLLOWED_BY field(kind, add) AND field(page, $p) DURING 10 minutes BETWEEN("2026-06-18T00:00:00Z", "2026-06-21T09:20:05Z") AGGREGATE count()', "c34-delete-then-resave-10min")
post('SELECT field(kind, delete) AND field(page, $p) FOLLOWED_BY field(kind, add) AND field(page, $p) DURING 1 day BETWEEN("2026-06-18T00:00:00Z", "2026-06-21T09:20:05Z") AGGREGATE count()', "c34-delete-then-resave-1day")
