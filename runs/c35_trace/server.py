"""C35 server cross-checks on wiki_msgs (signed swarmchasing-9d-c35, labelled). Rows, not saves, and the `signature`
column (last "-- Name" line of a hunk), so counts are not C28's; they check direction on the carrier.
sticky: a mismatched add, then the same signature under the same label within 10 min (twin: under another label);
chain: a mismatched add, then the signer's own name worn as a label by another signature within 10 min (twin: worn by
the signer itself); owner-then-borrow vs borrow-then-owner (the label signed by its own name, then by another, and
the reverse order). usage: python runs/c35_trace/server.py   (PRISMQL_URL, default http://localhost:8931)"""
import json, os, urllib.request
URL = os.environ.get("PRISMQL_URL", "http://localhost:8931")
MIS = 'field(kind, add) AND field(signature, $s) AND field(label, !$s) AND field(label, $L)'


def post(q, label):
    body = {"corpus": "wiki_msgs", "query": q + " AGGREGATE count()", "label": label}
    req = urllib.request.Request(URL + "/evaluate", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "X-PrismQL-Client": "swarmchasing-9d-c35"})
    try: r = json.load(urllib.request.urlopen(req, timeout=600))
    except urllib.error.HTTPError as e: r = json.load(e)
    print(label, "|", q, "\n   ->", r.get("value", r.get("error")), "| warnings:",
          [(w.get("code"), w.get("message")) for w in r.get("warnings") or []])


post(f"SELECT {MIS}", "c35-mismatch-rows")
post(f"SELECT {MIS} FOLLOWED_BY field(kind, add) AND field(signature, $s) AND field(label, $L) DURING 10 minutes", "c35-sticky-10min")
post(f"SELECT {MIS} FOLLOWED_BY field(kind, add) AND field(signature, $s) AND field(label, !$L) DURING 10 minutes", "c35-twin-sticky-otherlabel-10min")
post(f"SELECT {MIS} FOLLOWED_BY field(kind, add) AND field(label, $s) AND field(signature, !$s) DURING 10 minutes", "c35-chain-other-wears-signer-10min")
post(f"SELECT {MIS} FOLLOWED_BY field(kind, add) AND field(label, $s) AND field(signature, $s) DURING 10 minutes", "c35-twin-chain-signer-wears-own-10min")
post("SELECT field(kind, add) AND field(label, $L) AND field(signature, $L) FOLLOWED_BY field(kind, add) AND field(label, $L) AND field(signature, !$L) DURING 10 minutes", "c35-own-then-borrowed-10min")
post("SELECT field(kind, add) AND field(label, $L) AND field(signature, !$L) FOLLOWED_BY field(kind, add) AND field(label, $L) AND field(signature, $L) DURING 10 minutes", "c35-twin-borrowed-then-own-10min")
