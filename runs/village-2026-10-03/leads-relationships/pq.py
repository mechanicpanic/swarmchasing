"""pq.py: tiny PrismQL client for leads-relationships. fetch(out, corpus, query, dicts) -> JSONL with ids/times/bindings."""
import json, sys, urllib.request
BASE="http://localhost:8942"; HDR={"Content-Type":"application/json","X-PrismQL-Client":"leads-relationships"}
VERIFY=["verified your","checked your","confirmed your","tested your","double-checked your","rechecked your","re-checked your","verify your","can confirm","independently verified","independently confirmed","spot-checked","spot-check","cross-checked","I just verified","I verified","I double-checked","I can verify"]
DICTS={"verify":VERIFY}
def get(url, body=None):
    req=urllib.request.Request(BASE+url, data=json.dumps(body).encode() if body else None, headers=HDR)
    return json.load(urllib.request.urlopen(req, timeout=900))
def ev(corpus, query, max_results=10, explain=False, hydrate=True, dicts=DICTS):
    return get("/evaluate", {"corpus":corpus,"query":query,"max_results":max_results,"explain":explain,"hydrate":hydrate,"dictionaries":dicts,"label":"leads-relationships"})
def fetch(out, corpus, query, dicts=DICTS):
    first=ev(corpus, query, 50, True, False, dicts)
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
if __name__=='__main__':
    if sys.argv[1]=='fetch': fetch(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        r=ev(sys.argv[1], sys.argv[2], 5, True)
        print({k:v for k,v in r.items() if k not in('results',)})
        for g in r.get('results',[]):
            print('--', g.get('bindings'))
            for e in g.get('events',[]): print('   ',e.get('time','')[:16], e.get('agent'), repr(str(e.get('text',''))[:250]))
