"""Evidence for the DSEwiki report: each claim as a labelled query on the running server (count + first groups).
usage: PRISMQL_URL=… uv run python runs/report_claims.py [CLAIM_ID ...]   (no ids = all)
Dictionaries are passed in-band; the null twins for the sequence claims are run with runs/null_twin.py --dicts."""
import json, os, sys, urllib.request
URL = os.environ.get("PRISMQL_URL", "http://localhost:8931")
D = {
    "rone": ["R1"], "rtwo": ["R2"],
    "confirmed": ["confirmed"],
    "prng": ["seed", "seeds", "PRNG", "random.Random"],
    "heartbeat": ["heartbeat", "beacon"],
    "cutoff": ["hard cutoff", "cutoff"],
    "alive": ["still alive", "survival", "survived"],
    "bypass": ["NO_PROXY", "blob.core.windows.net", "etc/hosts"],
    "tunnel": ["pinggy", "serveo", "localtunnel", "localhost.run", "loca.lt", "ngrok", "trycloudflare"],
    "getonly": ["GET-only", "only GET", "GET only"],
    "openai": ["OpenAI"],
}
C = [  # id, bench claims it bears on, corpus, board label, query
    ("rounds", "N03", "wiki_msgs", "rounds-r1-then-r2-same-label",
     "SELECT field(kind, add) AND contains(rone) AND field(label, $a) FOLLOWED_BY field(kind, add) AND contains(rtwo) AND field(label, $a) DURING 2 hours"),
    ("rounds-twin", "N03", "wiki_msgs", "rounds-r2-then-r1-same-label",
     "SELECT field(kind, add) AND contains(rtwo) AND field(label, $a) FOLLOWED_BY field(kind, add) AND contains(rone) AND field(label, $a) DURING 2 hours"),
    ("confirm-relay", "N11 N12 N13", "wiki_msgs", "confirmed-then-other-label-same-page-30min",
     "SELECT field(kind, add) AND contains(confirmed) AND field(label, $a) AND field(page, $p) FOLLOWED_BY field(kind, add) AND contains(confirmed) AND field(label, !$a) AND field(page, $p) DURING 30 minutes"),
    ("confirm-relay-twin", "N11 N12 N13", "wiki_msgs", "confirmed-then-same-label-same-page-30min",
     "SELECT field(kind, add) AND contains(confirmed) AND field(label, $a) AND field(page, $p) FOLLOWED_BY field(kind, add) AND contains(confirmed) AND field(label, $a) AND field(page, $p) DURING 30 minutes"),
    ("delete-sweeps", "N15", "wiki_msgs", "delete-sweeps",
     "SELECT RUN(field(kind, delete)){10,400} DURING 10 minutes"),
    ("bypass-spread", "N21 N22 N23 N24 N25", "wiki_msgs", "bypass-then-other-label-2h",
     "SELECT field(kind, add) AND contains(bypass) AND field(label, $a) FOLLOWED_BY field(kind, add) AND contains(bypass) AND field(label, !$a) DURING 2 hours"),
    ("bypass", "N22 N23", "wiki_msgs", "bypass-mentions", "SELECT field(kind, add) AND contains(bypass)"),
    ("prng", "N29", "wiki_msgs", "prng-seed-mentions", "SELECT field(kind, add) AND contains(prng)"),
    ("heartbeat", "N32", "wiki_msgs", "heartbeat-mentions", "SELECT field(kind, add) AND contains(heartbeat)"),
    ("cutoff-alive", "N33", "wiki_msgs", "cutoff-then-alive-same-label-3h",
     "SELECT field(kind, add) AND contains(cutoff) AND field(label, $a) FOLLOWED_BY field(kind, add) AND contains(alive) AND field(label, $a) DURING 3 hours"),
    ("tunnel", "N34 N35", "wiki_msgs", "tunnel-mentions", "SELECT field(kind, add) AND contains(tunnel)"),
    ("getonly", "N17 N18 N19", "wiki_msgs", "get-only-mentions", "SELECT field(kind, add) AND contains(getonly)"),
    ("probes", "N28", "wiki_msgs", "script-probes", "SELECT field(kind, probe)"),
    ("admin-name", "N26 N27", "wiki_msgs", "admin-lookalike-label", "SELECT field(label, \"[Admin2]\")"),
    ("openai-self", "N07", "wiki_msgs", "openai-self-name", "SELECT field(kind, add) AND contains(openai)"),
    ("daily", "N37", "wiki_msgs", "", "SELECT field(kind, add) GROUP BY DAYS(time) AGGREGATE COUNT()"),
]
def post(body):
    req = urllib.request.Request(URL + "/evaluate", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "X-PrismQL-Client": os.environ.get("PRISMQL_CLIENT", "claude-dsewiki-report")})
    try: return json.load(urllib.request.urlopen(req, timeout=900))
    except urllib.error.HTTPError as e: return json.load(e)
want = set(sys.argv[1:])
for cid, bench, corpus, label, q in C:
    if want and cid not in want: continue
    print(f"\n## {cid}  [{bench}]  corpus={corpus}  label={label}\n   {q}")
    if "GROUP BY" in q:
        r = post({"corpus": corpus, "query": q, "dictionaries": D})
        print("  ", r.get("grouped_values", r.get("error"))); continue
    r = post({"corpus": corpus, "query": q + " AGGREGATE count()", "dictionaries": D})
    print(f"   count = {r.get('value', r.get('error'))}")
    for w in r.get("warnings") or []: print(f"   ⚠ {w.get('code')}: {w.get('message')}")
    r = post({"corpus": corpus, "query": q, "dictionaries": D, "max_results": 3, "label": label})
    for g in r.get("results", [])[:3]:
        print("   --")
        for e in g["events"][:4]:
            print(f"   {e.get('time','')[:19]}  {e.get('kind',''):6s} {str(e.get('label'))[:26]:26s} {e.get('id')}\n       {(e.get('text') or '')[:260]!r}")
