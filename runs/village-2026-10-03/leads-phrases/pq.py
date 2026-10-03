# Minimal PrismQL client: logs every query to queries.log; prints total + bindings summary.
import json, sys, urllib.request, datetime, collections
def q(query, corpus="village_chat", n=50, explain=True):
    body = json.dumps({"corpus": corpus, "query": query, "max_results": n, "explain": explain}).encode()
    req = urllib.request.Request("http://localhost:8942/evaluate", body, {"Content-Type":"application/json","X-PrismQL-Client":"phrase-births"})
    r = json.load(urllib.request.urlopen(req, timeout=300))
    with open("queries.log","a") as f:
        f.write(json.dumps({"at": str(datetime.datetime.now()), "corpus": corpus, "query": query, "total": r.get("total"), "result_id": r.get("result_id")})+"\n")
    return r
if __name__ == "__main__":
    r = q(sys.argv[1], sys.argv[2] if len(sys.argv)>2 else "village_chat", int(sys.argv[3]) if len(sys.argv)>3 else 50)
    print("total", r.get("total"), "result_id", r.get("result_id"))
    pairs = collections.Counter()
    for g in r.get("results", []):
        for b in g.get("bindings", [])[:1]:
            pairs[tuple(sorted(b.items()))] += 1
        ev = g.get("events", [])
    for p, c in pairs.most_common(40): print(c, dict(p))
