"""q.py CORPUS 'QUERY' [max] [--dict name=a,b;name2=c] -> prints total + compact groups; logs to queries.jsonl"""
import json, sys, urllib.request, datetime
corpus, query = sys.argv[1], sys.argv[2]
mx = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 5
dicts = {}
for a in sys.argv[3:]:
    if a.startswith("--dict"):
        for part in a.split("=", 1)[1].split(";"):
            k, v = part.split(":", 1); dicts[k] = v.split(",")
body = {"corpus": corpus, "query": query, "max_results": mx, "explain": True}
if dicts: body["dictionaries"] = dicts
req = urllib.request.Request("http://localhost:8953/evaluate", data=json.dumps(body).encode(),
      headers={"Content-Type": "application/json", "X-PrismQL-Client": "datasets"})
try:
    r = json.load(urllib.request.urlopen(req, timeout=600))
except urllib.error.HTTPError as e:
    print(e.read().decode()[:1500]); sys.exit(1)
open("/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/datasets/queries.jsonl", "a").write(
    json.dumps({"t": datetime.datetime.now().isoformat(), "corpus": corpus, "query": query, "dicts": dicts,
                "total": r.get("total"), "result_id": r.get("result_id")}) + "\n")
print("total", r.get("total"), "result_id", r.get("result_id"), "warnings", r.get("warnings"))
extra={k:v for k,v in r.items() if k not in ("results","explain","query","ok","warnings","result_id","total","count","truncated","max_results","corpus","timing","activity_id")}
if extra: print(json.dumps(extra)[:3000])
for g in r.get("results", [])[:mx]:
    print("---", (g.get("bindings") or "")[:3] if g.get("bindings") else "")
    for e in g.get("events", []):
        print(f"  {str(e.get('time'))[:19]} {e.get('kind','')[:8]:8} {str(e.get('actor'))[:28]:28} {str(e.get('page',''))[:40]:40} | {str(e.get('text',''))[:160]!r}")
