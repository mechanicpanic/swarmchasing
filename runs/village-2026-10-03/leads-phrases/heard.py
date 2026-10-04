# "Who heard it from whom" via two PrismQL queries joined on event id:
#  Q1 first use per agent:  X AND field(agent,$b) NOT_PRECEDED_BY X AND field(agent,$b) DURING 400 days
#  Q2 nearest earlier user: X AND field(agent,$b) PRECEDED_BY X AND field(agent,$a) AND field(agent,!$b) DURING <win>
# explain:true returns $a/$b bindings per group.
import json, sys, urllib.request, pq
def allgroups(r):
    rid = r.get("result_id")
    if not rid or not r.get("truncated"): return r.get("results", [])
    out = []
    with urllib.request.urlopen(urllib.request.Request(f"http://localhost:8942/results/{rid}.jsonl?explain=true", headers={"X-PrismQL-Client":"phrase-births"})) as f:
        for line in f: out.append(json.loads(line))
    return out
def heard(X, win="1 hour", corpus="village_chat"):
    p = f'contains_phrase("{X}")'
    fu = allgroups(pq.q(f'SELECT {p} AND field(agent, $b) NOT_PRECEDED_BY {p} AND field(agent, $b) DURING 400 days', corpus, 500))
    first = {g["events"][0]["id"]: (g["events"][0]["agent"], g["events"][0]["time"][:16]) for g in fu}
    ch = allgroups(pq.q(f'SELECT {p} AND field(agent, $b) PRECEDED_BY {p} AND field(agent, $a) AND field(agent, !$b) DURING {win}', corpus, 500))
    src = {}
    for g in ch:
        ev = g["events"]; b = ev[-1]
        if b["id"] in first:
            bd = (g.get("bindings") or [{}])[0]
            src[b["id"]] = (bd.get("a") or ev[0]["agent"], ev[0]["time"][:16])
    rows = sorted(first.items(), key=lambda kv: kv[1][1])
    return [(agent, t, *(src.get(i, (None, None)))) for i, (agent, t) in rows]
if __name__ == "__main__":
    for X in sys.argv[1:]:
        print("==", X)
        for agent, t, a, ta in heard(X): print(f"  {t} {agent:28s} <- {a or '(no use by another agent in prior hour)'} {ta or ''}")
