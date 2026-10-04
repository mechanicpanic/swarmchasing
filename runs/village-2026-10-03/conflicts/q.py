#!/usr/bin/env python3
"""Tiny client: q.py CORPUS 'QUERY' [max] [--explain] [--count] -> prints groups briefly."""
import json, sys, urllib.request
H={'Content-Type':'application/json','X-PrismQL-Client':'conflicts'}
def ev(corpus, query, max_results=20, explain=False, dictionaries=None, hydrate=True):
    body={'corpus':corpus,'query':query,'max_results':max_results,'explain':explain,'hydrate':hydrate}
    if dictionaries: body['dictionaries']=dictionaries
    r=urllib.request.Request('http://localhost:8942/evaluate',json.dumps(body).encode(),H)
    try:
        return json.load(urllib.request.urlopen(r,timeout=900))
    except urllib.error.HTTPError as e:
        return {'error':e.read().decode()}
def stream(result_id):
    r=urllib.request.Request(f'http://localhost:8942/results/{result_id}.jsonl',headers=H)
    for line in urllib.request.urlopen(r,timeout=900):
        yield json.loads(line)
if __name__=='__main__':
    c,q=sys.argv[1],sys.argv[2]; n=int(sys.argv[3]) if len(sys.argv)>3 and sys.argv[3].isdigit() else 10
    res=ev(c,q,n,'--explain' in sys.argv)
    if 'error' in res: print(res['error']); sys.exit(1)
    print('total',res.get('total'),'truncated',res.get('truncated'),'rid',res.get('result_id'), res.get('warnings'))
    if 'value' in res or 'grouped_values' in res: print(json.dumps({k:v for k,v in res.items() if k!='results'})[:3000])
    for g in res.get('results',[]):
        print('----', g.get('bindings',''))
        for e in g.get('events',[]):
            print(f"  [{e.get('time','')[:16]}] {e.get('kind')} {e.get('agent')}: {str(e.get('text',''))[:400]!r}")
