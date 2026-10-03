# tiny PrismQL client; logs every query to queries.log
import json, sys, urllib.request, datetime

def q(query, corpus="village_chat", max_results=20, explain=True, **kw):
    body = dict(corpus=corpus, query=query, max_results=max_results, explain=explain, **kw)
    req = urllib.request.Request("http://localhost:8942/evaluate", data=json.dumps(body).encode(),
          headers={"Content-Type": "application/json", "X-PrismQL-Client": "contagion"})
    r = json.load(urllib.request.urlopen(req, timeout=600))
    with open("queries.log", "a") as f:
        f.write(json.dumps(dict(at=str(datetime.datetime.now()), corpus=corpus, query=query,
                                total=r.get("total"), result_id=r.get("result_id"))) + "\n")
    return r

def stream(result_id):
    req = urllib.request.Request(f"http://localhost:8942/results/{result_id}.jsonl?explain=true",
                                 headers={"X-PrismQL-Client": "contagion"})
    return [json.loads(l) for l in urllib.request.urlopen(req, timeout=600)]

if __name__ == "__main__":
    r = q(sys.argv[1], corpus=sys.argv[2] if len(sys.argv) > 2 else "village_chat",
          max_results=int(sys.argv[3]) if len(sys.argv) > 3 else 8)
    if "error" in r: print(r); sys.exit()
    print("total", r.get("total"), "result_id", r.get("result_id"))
    for g in r.get("results", []):
        print("---", g.get("bindings"))
        for e in g["events"]:
            print(f'  [{str(e.get("time",""))[:19]}] {e.get("agent")} ({e.get("room")}): {e.get("text","")[:260]!r}')
