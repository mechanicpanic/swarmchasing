"""Queries against the running server, signed as `claude` for the board.
usage: python runs/ask.py CORPUS < queries
  # heading        echoed
  QUERY            run with AGGREGATE count() appended
  @label QUERY     run for groups (max 20) under that board label; prints group count and the first group"""
import os, sys, json, urllib.request
URL = os.environ.get("PRISMQL_URL", "http://localhost:8931")
corpus = sys.argv[1]
def warn(r):
    for w in r.get("warnings") or []:
        print(f"         ⚠ {w.get('code')}: {w.get('message')}" + (f"  → {w.get('suggestion')}" if w.get('suggestion') else ""))
def post(body):
    req = urllib.request.Request(URL + "/evaluate", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "X-PrismQL-Client": "claude"})
    try: return json.load(urllib.request.urlopen(req, timeout=600))
    except urllib.error.HTTPError as e: return json.load(e)
for line in sys.stdin:
    q = line.strip()
    if not q: continue
    if q.startswith('#'): print(q); continue
    if q.startswith('@'):
        label, q = q[1:].split(' ', 1)
        r = post({"corpus": corpus, "query": q, "max_results": 20, "label": label})
        if 'error' in r: print(f"ERROR    {q}\n         {r['error'].get('message')}"); continue
        res = r.get('results', [])
        print(f"{len(res):>3}{'+' if r.get('truncated') else ' '} grp  [{label}] {q}   [{r.get('elapsed_ms','?')} ms]")
        warn(r)
        for e in (res[0]['events'] if res else []):
            print(f"           {e.get('time','')[:19]}  {e.get('kind','')[:24]:24s} {str(e.get('agent') or '-')[:22]:22s} {(e.get('text') or '')[:90]!r}")
        continue
    r = post({"corpus": corpus, "query": q + " AGGREGATE count()"})
    v = r.get("value", r.get("grouped_values", (r.get("error") or {}).get("message", r.get("detail"))))
    print(f"{str(v):8s} {q}   [{r.get('elapsed_ms','?')} ms]"); warn(r)
