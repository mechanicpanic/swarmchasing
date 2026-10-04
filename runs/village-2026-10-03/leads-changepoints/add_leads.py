# Append leads (JSON list on stdin) to leads.jsonl with sequential ids.
import json, sys, os
P = os.path.join(os.path.dirname(__file__), "leads.jsonl")
n = sum(1 for _ in open(P)) if os.path.exists(P) else 0
FORBID = ["Terra", "Luna"]
with open(P, "a") as f:
    for L in json.load(sys.stdin):
        n += 1
        s = json.dumps(L, ensure_ascii=False)
        assert not any(w in s for w in FORBID), L["hook"]
        L = {"id": f"changepoints-{n}", "generator": "changepoints", **L}
        f.write(json.dumps(L, ensure_ascii=False) + "\n")
print(n, "leads total")
