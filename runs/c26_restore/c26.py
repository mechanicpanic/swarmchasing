"""C26 (report §14): R2 re-tested. Authors recomputed as the latest earlier adder; distinct restoring saves;
whole-save nulls within (day, page) and (5-min, page). usage (repo root): uv run python runs/c26_restore/c26.py --mode repro|real|null [--n 1000 --strata day|m5]. REPO = repo root."""
import os
"""C26: removal by another label -> the text's author re-adds the same text on the same page within W.
Author = latest label that added text_key on the page in a STRICTLY EARLIER save than the removal.
Restore = first add of that text_key on that page by the author in a strictly later save; matched if gap <= W.
Count = distinct restoring revs. Null: whole saves (all add/remove rows of a rev) permuted over the (time, order)
slots of the saves in the same stratum (day,page) or (m5,page); author recomputed in every permutation.
usage: python c26.py [--n 200] [--strata day|m5] [--mode real|null|repro|dump]"""
import argparse, gzip, json, random, statistics, sys
from collections import defaultdict
import polars as pl

sys.path.insert(0, os.path.join(os.environ.get("REPO", "."), "prepare"))
from textkey import key

R = os.environ.get("REPO", ".") + "/"
WIN = {"1min": 60, "10min": 600, "1h": 3600}
HUB, J18 = "dse~WillkommenImWiki", "2026-06-18"

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=200)
ap.add_argument("--strata", default="day")
ap.add_argument("--mode", default="real")
a = ap.parse_args()

df = (pl.read_parquet(R + "data/wiki_msgs.parquet", columns=["id", "time", "seq", "page", "label", "rev", "kind", "hunk", "op", "text", "text_key", "author_label"])
      .filter(pl.col("kind").is_in(["add", "remove"]) & pl.col("text_key").is_not_null()).sort("seq"))
revs = {json.loads(l)["rev_id"]: json.loads(l) for l in gzip.open(R + "data/collusion_wiki/revisions.jsonl.gz", "rt")}
bodykey = {r: key(v.get("body") or "") for r, v in revs.items()}
unpub = {r for r, v in revs.items() if v.get("diff_base_reason") == "earlier_revisions_not_published"}

rows = df.to_dicts()
_ls = lambda r: {x.strip() for x in (revs[r].get("body") or "").split("\n") if x.strip()} if r else set()
def _frac(r):  # share of the base page's non-empty lines this save took away
    b = _ls(revs[r].get("diff_base")); return 1.0 if not b else 1 - len(b & _ls(r)) / len(b)
frac = {r: _frac(r) for r in set(df["rev"].to_list())}
for d in rows:
    rv = revs[d["rev"]]
    d["t"] = d["time"].timestamp()
    d["whole"] = (bodykey[d["rev"]] == d["text_key"]) if d["kind"] == "add" else \
                 (rv.get("diff_base") is not None and bodykey[rv["diff_base"]] == d["text_key"])
    d["day"] = d["time"].strftime("%Y-%m-%d")
    d["m5"] = d["time"].strftime("%Y-%m-%dT%H:") + str(d["time"].minute // 5 * 5)
    d["ko"] = 0 if d["kind"] == "add" else 1
    d["small"] = frac[d["rev"]] < 0.5

# save slots: (t, first seq) per rev; strata by page + day/m5 of the save
save = {}
for d in rows:
    save.setdefault(d["rev"], (d["t"], d["seq"], d["page"], d[a.strata] if a.strata != "none" else None))
strata = defaultdict(list)
for r, (t, s, p, k) in save.items():
    strata[(p, k)].append(r)


def match(slot, author_mode="latest"):
    """slot: rev -> (t, seq). Returns list of (remove_row, restore_row_any, restore_row_msglevel)."""
    groups = defaultdict(list)
    for d in rows:
        groups[(d["page"], d["text_key"])].append(d)
    out = []
    for g in groups.values():
        if not any(x["kind"] == "remove" for x in g) or not any(x["kind"] == "add" for x in g):
            continue
        g.sort(key=lambda x: (slot[x["rev"]], x["hunk"], x["ko"]))
        for i, x in enumerate(g):
            if x["kind"] != "remove":
                continue
            xs = slot[x["rev"]]
            if author_mode == "first":
                au = x["author_label"]
            else:
                au = None
                for y in reversed(g[:i]):
                    if y["kind"] == "add" and slot[y["rev"]] < xs:
                        au = y["label"]; break
            if au is None or au == x["label"]:
                continue
            r_any = r_msg = r_s = None
            for y in g[i + 1:]:
                if y["kind"] == "add" and y["label"] == au and slot[y["rev"]] > xs:
                    if r_any is None: r_any = y
                    if not y["whole"] and r_msg is None: r_msg = y
                    if not y["whole"] and y["small"]: r_s = y; break
            out.append((x, r_any, r_msg, xs, r_s))
    return out


def pick(var, x, ra, rm, rs):
    if var == "all": return ra
    if var == "msg": return rm if not x["whole"] else None
    if var == "msgR": return rs if not x["whole"] else None
    return rs if (not x["whole"] and x["small"]) else None


def cells(slot, ms):
    """variant x scope x window -> distinct restoring revs"""
    res = {}
    for var in ("all", "msg", "msgR", "msgS"):
        for scope in ("full", "noHub", "noJ18", "noHub_noJ18"):
            for wn, w in WIN.items():
                revset = set()
                for x, ra, rm, xs, rs in ms:
                    y = pick(var, x, ra, rm, rs)
                    if y is None: continue
                    ys = slot[y["rev"]]
                    if ys[0] - xs[0] > w: continue
                    if "noHub" in scope and x["page"] == HUB: continue
                    if "noJ18" in scope:
                        import time as _tm
                        if _tm.strftime("%Y-%m-%d", _tm.gmtime(xs[0])) == J18 or \
                           _tm.strftime("%Y-%m-%d", _tm.gmtime(ys[0])) == J18: continue
                    revset.add(y["rev"])
                res[(var, scope, wn)] = len(revset)
    return res


real_slot = {r: (v[0], v[1]) for r, v in save.items()}
if a.mode == "repro":
    ms = match(real_slot, "first")
    m = [(x, ra) for x, ra, rm, xs, rs in ms if ra and real_slot[ra["rev"]][0] - xs[0] <= 60]
    print("repro (author_label, first add by author, 1min): matches", len(m), "distinct rows", len({ra["id"] for _, ra in m}), "distinct revs", len({ra["rev"] for _, ra in m}))
    ms = match(real_slot)
    m = [(x, ra) for x, ra, rm, xs, rs in ms if ra and real_slot[ra["rev"]][0] - xs[0] <= 60]
    print("latest-author, 1min: matches", len(m), "distinct revs", len({ra["rev"] for _, ra in m}))
    ww = sum(1 for x, ra in m if x["whole"] and ra["whole"]); rr = sum(1 for x, ra in m if x["op"] == "replace" and ra["op"] == "replace")
    print("  whole->whole pairs", ww, " replace->replace", rr, " removal whole", sum(x["whole"] for x, _ in m), " restore whole", sum(ra["whole"] for _, ra in m), " unpub-base restores", sum(ra["rev"] in unpub for _, ra in m))
    sys.exit()
if a.mode == "dump":
    ms = match(real_slot)
    out = []
    for x, ra, rm, xs, rs in ms:
        for var in ("all", "msg", "msgR", "msgS"):
            y = pick(var, x, ra, rm, rs)
            if y is None: continue
            gap = real_slot[y["rev"]][0] - xs[0]
            if gap <= 3600:
                out.append(dict(var=var, rm_id=x["id"], rm_label=x["label"], author=y["label"], rs_id=y["id"], rs_rev=y["rev"], gap=gap,
                                page=x["page"], day=x["day"], rm_whole=x["whole"], rs_whole=y["whole"], rm_op=x["op"], rs_op=y["op"], text=x["text"][:300]))
    pl.DataFrame(out).write_parquet(__import__("os").path.dirname(__import__("os").path.abspath(__file__)) + "/real_pairs.parquet")
    print(len(out)); sys.exit()

real = cells(real_slot, match(real_slot))
if a.mode == "real":
    for k, v in real.items(): print(k, v)
    sys.exit()
nulls = defaultdict(list)
for i in range(a.n):
    rng = random.Random(i)
    slot = {}
    for rs in strata.values():
        sl = [real_slot[r] for r in rs]; perm = sl[:]; rng.shuffle(perm)
        slot.update(zip(rs, perm))
    for k, v in cells(slot, match(slot)).items(): nulls[k].append(v)
    if i % 50 == 49: print("..", i + 1, file=sys.stderr, flush=True)
res = []
for k, v in real.items():
    ns = sorted(nulls[k])
    res.append(dict(variant=k[0], scope=k[1], window=k[2], real=v, null_median=statistics.median(ns), null_p95=ns[int(0.95 * a.n) - 1],
                    null_max=ns[-1], share_ge_real=sum(n >= v for n in ns) / a.n))
out = pl.DataFrame(res)
out.write_csv(__import__("os").path.dirname(__import__("os").path.abspath(__file__)) + f"/null_{a.strata}_n{a.n}.csv")
with pl.Config(tbl_rows=50, tbl_width_chars=200):
    print(out)
