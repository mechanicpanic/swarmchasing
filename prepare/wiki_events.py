"""collusion.wiki export (data/collusion_wiki/, `make wiki-data`) → the two original wiki streams.
data/collusion_wiki_events.jsonl: one row per wiki operation (save/delete/probe/revert), ordered by reconciled time;
a save takes its label and /16 from its revision, every row its page family from pages.jsonl.
data/collusion_wiki_revisions.jsonl: one row per saved page version in export order, with the whole page as `text`."""

import gzip
import json

W = "data/collusion_wiki/"


def jsonl(name):
    with gzip.open(W + name, "rt") as fh:
        return [json.loads(line) for line in fh]


revs = jsonl("revisions.jsonl.gz")
rev = {r["rev_id"]: r for r in revs}
fam = {p["page_key"]: p["page_family"] for p in jsonl("pages.jsonl.gz")}

events = []
for e in jsonl("events.jsonl.gz"):
    r = rev.get(e.get("revision_ref")) if e["event_type"] == "save" else None
    events.append(
        {
            "id": e["event_id"],
            "event_type": e["event_type"],
            "page": e.get("page_key"),
            "label": r["label"] if r else e.get("actor_label"),
            "ip16": r["ip16"] if r else e.get("ip16"),
            "page_family": fam.get(e.get("page_key")),
            "time": e["time"],
        }
    )
events.sort(key=lambda e: e["time"])  # stable: ties keep export order

with open("data/collusion_wiki_events.jsonl", "w") as fh:
    for e in events:
        fh.write(json.dumps(e) + "\n")
with open("data/collusion_wiki_revisions.jsonl", "w") as fh:
    for r in revs:
        row = {
            "id": r["rev_id"],
            "time": r["time"],
            "user": r["label"],
            "label": r["label"],
            "ip16": r["ip16"],
            "wiki": r["wiki"],
            "page": r["page_key"],
            "page_family": fam.get(r["page_key"]),
            "seq": r["seq"],
            "body_len": r["body_len"],
            "text": r.get("body") or "",
        }
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
print(len(events), "events,", len(revs), "revisions")
