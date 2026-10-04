import json, sys, urllib.request
DICTS = {
 "accuse": ["doesn't exist","does not exist","don't exist","do not exist","doesn’t exist","don’t exist","didn't exist","didn’t exist",
            "nonexistent","non-existent","phantom","fabricated","fabricating","fabrication","never existed","isn't real","is not real"],
 "artifact": ["pr","prs","pull request","commit","commits","branch","file","files","link","url","sheet","doc","document","repo","issue","page","post","form"],
 "retract": ["i was wrong","i was incorrect","was wrong","was incorrect","my mistake","my error","my bad","apologize","apologise","apologies","apology","retract","does exist","do exist","i stand corrected","i was mistaken","i misspoke"],
}
def ev(query, label, max_results=5, explain=False, hydrate=False):
    body = {"corpus":"village","query":query,"dictionaries":DICTS,"label":label,"max_results":max_results,"hydrate":hydrate}
    if explain: body["explain"]=True
    req = urllib.request.Request("http://localhost:8931/evaluate", data=json.dumps(body).encode(),
        headers={"Content-Type":"application/json","X-PrismQL-Client":"swarmchasing-9d-c12"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=600))
    except urllib.error.HTTPError as e:
        return json.loads(e.read())
def page(rid, total):
    out=[]; off=0
    while off < total:
        r=json.load(urllib.request.urlopen(urllib.request.Request(f"http://localhost:8931/results/{rid}?offset={off}&limit=500&hydrate=false",headers={"X-PrismQL-Client":"swarmchasing-9d-c12"})))
        items=r.get('results') or r.get('items') or []
        if not items: break
        out+=items; off+=len(items)
    return out
if __name__=="__main__":
    r=ev(sys.argv[1], sys.argv[2])
    print(json.dumps({k:v for k,v in r.items() if k not in ('results',)} , indent=1)[:2000])
