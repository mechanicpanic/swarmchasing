"""fetch.py OUT CORPUS QUERY -> every group with bindings as JSONL (explain pages)."""
import json, sys, urllib.request
BASE="http://localhost:8942"; HDR={"Content-Type":"application/json","X-PrismQL-Client":"conflicts"}
D=json.load(open('/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/conflicts/dicts.json'))
def get(url, body=None):
    req=urllib.request.Request(BASE+url, data=json.dumps(body).encode() if body else None, headers=HDR)
    return json.load(urllib.request.urlopen(req, timeout=900))
out, corpus, query = sys.argv[1:4]
first=get("/evaluate", {"corpus":corpus,"query":query,"max_results":50,"hydrate":False,"explain":True,"dictionaries":D,"label":"conflicts"})
rid,total=first.get("result_id"),first["total"]; print('total',total, first.get('warnings'))
n=off=0
with open(out,"w") as f:
    while off<total:
        page=first if off==0 else get(f"/results/{rid}?offset={off}&limit=50&explain=true")
        for g in page["results"]:
            f.write(json.dumps({k:g[k] for k in ("ids","times","bindings") if k in g})+"\n"); n+=1
        off+=page["count"]
        if page["count"]==0: break
print(out,'groups',n)
