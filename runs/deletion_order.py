"""Do the admin's deletion sweeps run in page-name order?  Sweeps = the server's RUN(field(kind, delete)){10,400}
DURING 10 minutes groups; statistic = share of consecutive deletions in a sweep whose page names ascend (ASCII,
wiki prefix dropped). Null: page names permuted among the deletions of the same UTC day (keeps every time and
sweep, breaks which page went when), n permutations.  usage: uv run python runs/deletion_order.py [--n 1000]"""
import argparse, json, os, random, urllib.request
from collections import defaultdict
ap = argparse.ArgumentParser(); ap.add_argument('--n', type=int, default=1000); a = ap.parse_args()
URL = os.environ.get("PRISMQL_URL", "http://localhost:8931")
def post(body):
    req = urllib.request.Request(URL + "/evaluate", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "X-PrismQL-Client": "claude-dsewiki-report"})
    return json.load(urllib.request.urlopen(req, timeout=600))
Q = "SELECT RUN(field(kind, delete)){10,400} DURING 10 minutes"
r = post({"corpus": "wiki_msgs", "query": Q, "max_results": 100, "label": "delete-sweeps"})
groups = r["results"]
while len(groups) < r["total"]:  # page the kept result
    with urllib.request.urlopen(f"{URL}/results/{r['result_id']}?offset={len(groups)}&limit=100") as f:
        groups += json.load(f)["results"]
sweeps = [[(e["time"], e["page"].split("~", 1)[1]) for e in g["events"]] for g in groups]
asc = lambda names: sum(x <= y for x, y in zip(names, names[1:]))
def score(sw):  # per period: (ascending pairs, pairs)
    out = defaultdict(lambda: [0, 0])
    for s in sw:
        names = [p for _, p in s]; per = s[0][0][:10]
        k = 'Jun 18-20' if per <= '2026-06-20' else ('Jul 12-14' if per >= '2026-07-12' else 'Jun 22-Jul 11')
        for key in (k, 'all'): out[key][0] += asc(names); out[key][1] += len(names) - 1
    return {k: v[0] / v[1] for k, v in out.items()}, {k: v[1] for k, v in out.items()}
real, pairs = score(sweeps)
by_day = defaultdict(list)  # (sweep index, position) per day, to permute names within the day
for i, s in enumerate(sweeps):
    for j, (t, p) in enumerate(s): by_day[t[:10]].append((i, j, p))
nulls = defaultdict(list)
for k in range(a.n):
    rng = random.Random(k); sw = [list(s) for s in sweeps]
    for day, slots in by_day.items():
        names = [p for _, _, p in slots]; rng.shuffle(names)
        for (i, j, _), p in zip(slots, names): sw[i][j] = (sw[i][j][0], p)
    for key, v in score(sw)[0].items(): nulls[key].append(v)
print(f"sweeps: {len(sweeps)} ({sum(len(s) for s in sweeps)} deletions)   query: {Q}")
for key in ['Jun 18-20', 'Jun 22-Jul 11', 'Jul 12-14', 'all']:
    ns = sorted(nulls[key]); p95 = ns[int(0.95 * a.n) - 1]
    print(f"{key:14s} pairs {pairs[key]:5d}  ascending {real[key]:.3f}   null median {ns[a.n // 2]:.3f} 95th {p95:.3f} max {ns[-1]:.3f}"
          f"   {'clears 95th' if real[key] > p95 else 'within null'}")
