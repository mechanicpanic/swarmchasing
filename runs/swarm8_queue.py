"""Review queue "Swarm 8": saves whose writer name (label) is not the signature in the text they added, each shown with
the label's previous save and the signature's own saves as a label before and after — to tell rotation, a borrowed name
and a shared name apart (Mermachine's finding 3, and her follow-up). Writes tools/review/queues/swarm8.json.
usage: uv run python runs/swarm8_queue.py [--n 30] [--seed 8] [--data data/wiki_msgs.parquet]"""
import argparse, json, random, re, time
from pathlib import Path
import polars as pl

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=30); ap.add_argument("--seed", type=int, default=8)
ap.add_argument("--data", default="data/wiki_msgs.parquet"); ap.add_argument("--out", default="tools/review/queues/swarm8.json")
a = ap.parse_args()

SIG = re.compile(r"--\s*([A-Za-z][\w$()+%.-]{2,})\s*$")  # a line ending in "-- Name"
f = pl.read_parquet(a.data).filter(pl.col("kind") == "add").sort("seq")
rows = f.select("id", "seq", "time", "kind", "label", "page", "rev", "text", "add_type").to_dicts()
def signature(text):
    last = None
    for line in (text or "").splitlines():
        m = SIG.search(line.strip())
        if m: last = m.group(1)
    return last
by_label = {}
for i, r in enumerate(rows):
    by_label.setdefault(r["label"], []).append(i)
signed = [(i, s) for i, r in enumerate(rows) if (s := signature(r["text"]))]
mism = [(i, s) for i, s in signed if rows[i]["label"] and s != rows[i]["label"]]
print(f"{len(signed)} signed add rows, {len(mism)} with a signature that is not the label ({len(mism)/len(signed):.0%})")

def ev(i, role):
    if i is None: return {"id": f"none-{role}", "role": role, "none": True}
    r = rows[i]
    return {"id": r["id"], "time": r["time"].isoformat().replace("+00:00", "Z"), "role": role, "label": r["label"],
            "page": r["page"], "rev": r["rev"], "text": r["text"], "add_type": r["add_type"]}
def before(lst, i):
    j = [k for k in lst if k < i]; return j[-1] if j else None
def after(lst, i):
    j = [k for k in lst if k > i]; return j[0] if j else None

random.seed(a.seed)
items = []
for i, s in sorted(random.sample(mism, min(a.n, len(mism)))):
    lab = rows[i]["label"]; L = by_label.get(lab, []); S = by_label.get(s, [])
    evs = [ev(i, "this save"), ev(before(L, i), "same name, before"), ev(before(S, i), "signature as a name, before"),
           ev(after(S, i), "signature as a name, after")]
    b = {"name": lab, "signature": s}
    items.append({"key": rows[i]["id"], "group": {"ids": [e["id"] for e in evs], "events": evs, "bindings": [b]}})
q = {"id": "swarm8", "mode": "query", "server": "local", "corpus": "wiki_msgs", "created": time.time(), "total": len(mism),
     "name": "Swarm 8: a save signed by another name than the one it was saved under — rotation, a borrowed name, or a shared one?",
     "query": "(built in Python: runs/swarm8_queue.py) add rows whose last '-- Name' signature is not the label; "
              "with the label's previous save and the signature's saves as a label before and after",
     "items": items}
Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(json.dumps(q))
print(a.out, len(items), "items")
