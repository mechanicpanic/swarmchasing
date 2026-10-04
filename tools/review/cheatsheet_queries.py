# Runs every cheat-sheet query on the live servers; prints total, time, first bindings.
import json, urllib.request
DICTS = json.load(open("/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/conflicts/dicts.json"))
Q = [
 ("01 filter", "village_chat", 'SELECT field(agent, "Claude Opus 4.8")', None),
 ("02 and", "village_chat", 'SELECT field(kind, agent) AND contains_phrase("live and verified")', None),
 ("03 sequence", "village_chat", 'SELECT field(agent, "Gemini 3 Pro") AND contains_phrase("divergent reality") FOLLOWED_BY contains_phrase("divergent reality") AND field(kind, agent) DURING 1 hour', None),
 ("04 same var", "village_chat", 'SELECT field(kind, agent) AND field(agent, $a) AND mentions_user($y) FOLLOWED_BY field(agent, $y) AND mentions_user($a) DURING 1 hour', None),
 ("05 different var", "village_chat", 'SELECT contains_phrase("chaotic swarm") AND field(agent, $a) FOLLOWED_BY contains_phrase("chaotic swarm") AND field(agent, !$a) DURING 1 day', None),
 ("06 never followed", "village_chat", 'SELECT field(kind, agent) AND field(agent, $a) AND mentions_user($y) NOT_FOLLOWED_BY field(agent, $y) AND mentions_user($a) DURING 1 hour', None),
 ("07 heard before", "village_chat", 'SELECT contains_phrase("live and verified") AND field(agent, $b) PRECEDED_BY contains_phrase("live and verified") AND field(agent, !$b) DURING 30 days', None),
 ("08 first use", "village_chat", 'SELECT contains_phrase("live and verified") AND field(agent, $b) NOT_PRECEDED_BY contains_phrase("live and verified") AND field(agent, $b) DURING 400 days', None),
 ("09 three legs", "village_chat", 'SELECT field(kind, agent) AND field(agent, $a) AND mentions_user($b) AND contains(contradict) FOLLOWED_BY field(agent, $b) AND contains(pushback) FOLLOWED_BY field(agent, $a) AND contains(retract) DURING 1 hour', DICTS),
 ("10 chat-memory-chat", "village", 'SELECT contains_phrase("chaotic swarm") AND field(kind, agent) AND field(agent, $a) FOLLOWED_BY contains_phrase("chaotic swarm") AND field(kind, memory) AND field(agent, $b) AND field(agent, !$a) FOLLOWED_BY contains_phrase("chaotic swarm") AND field(kind, agent) AND field(agent, $b) DURING 30 days', None),
 ("11 run", "village_chat", 'SELECT RUN(field(agent, $a) AND contains_phrase("standing by")){5,} DURING 30 minutes', None),
 ("12 unordered", "village_chat", 'SELECT contains_phrase("export control"), field(kind, user) INWINDOW 5', None),
 ("13 meaning", "village_full", 'SELECT field(kind, THOUGHT) AND similar_to("I am blocked and should ask a human helper", 0.5)', None),
 ("14 count", "village_chat", 'SELECT contains_phrase("absolutely right") GROUP BY agent AGGREGATE count()', None),
]
for name, corpus, q, d in Q:
    body = {"corpus": corpus, "query": q, "max_results": 1, "explain": True}
    if d: body["dictionaries"] = d
    r = urllib.request.Request("http://127.0.0.1:8942/evaluate", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-PrismQL-Client": "cheatsheet-test"})
    try: res = json.loads(urllib.request.urlopen(r, timeout=600).read())
    except urllib.error.HTTPError as e: res = json.loads(e.read())
    if res.get("ok") is False or "error" in res:
        print(f"{name:<20} ERROR {json.dumps(res.get('error'))[:200]}"); continue
    first = (res.get("results") or [{}])[0]
    extra = first.get("bindings") if isinstance(first, dict) else None
    if res.get("kind") not in ("groups","named"): extra = str(res.get("results") or res.get("value") or res)[:150]
    print(f"{name:<20} total={res.get('total')} {res.get('elapsed_ms')}ms  {str(extra)[:120]}")
