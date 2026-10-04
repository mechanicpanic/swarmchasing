"""C32: synchronised stops. Do many labels make their last save within seconds of each other, more than their own
save rhythm predicts? Units are saves (one revision = one save) from the revisions export.
Exclusions: [Admin1], empty labels, the 17 'earlier_revisions_not_published' revisions, saves that add the Loop
broadcast (text_key 146d7f0c0cfc7856), redirect bodies; --nohub also drops dse~WillkommenImWiki.
Ends (one per unit):
  day      last save of a label in a UTC day, labels with a save in the day's last hour [T_D-3600, T_D]
  session  last save of a label before a gap >= 1 h (anywhere on the wiki); assigned to the day of the end
  page     last save of a label on one page before a gap >= 1 h on that page; statistic taken per page
Statistic: max number of units (= distinct labels) ending inside any w-second window (w = 10, 30, 60), per day.
Null: each unit's end moves to a uniformly random one of its own saves in its last hour (day: the day's last hour;
session/page: [end-3600, end]); n draws. Start twin (--starts): the same for first saves / first hour.
Variants: --informative keeps only units with >= 2 distinct save times in that hour (the ones the null can move);
--drop '= DZFASTMD' removes the saves of one page template (the June 18 welcome-page script) to see what is left.
Output: per day real / null mean / p95 / p for w = 10, 30, 60; per busy page (page mode); the top real windows
with their member saves, each member's next (or, with --starts, previous) save anywhere, and distinct /16s.
usage (repo root): REPO=. python runs/c32_stops/c32.py [--n 1000] [--mode day|session|page] [--nohub] [--starts]
                   [--informative] [--drop PREFIX]   -> $OUT/c32_<mode>[_nohub][_starts][_inf][_nodz].json"""
import argparse, gzip, json, os, re
from collections import defaultdict
import numpy as np
import polars as pl

R = os.environ.get("REPO", ".") + "/"
OUT = os.environ.get("OUT", "results/c32_stops")
HUB, BROADCAST = "dse~WillkommenImWiki", "146d7f0c0cfc7856"
REDIR = re.compile(r"(?i)^\s*#(redirect|weiterleitung)")
WS, GAP, HOUR = (10, 30, 60), 3600, 3600


def load(nohub, drop=None):
    revs = [json.loads(l) for l in gzip.open(R + "data/collusion_wiki/revisions.jsonl.gz", "rt")]
    bc = set(pl.read_parquet(R + "data/wiki_msgs.parquet", columns=["rev", "text_key"])
             .filter(pl.col("text_key") == BROADCAST)["rev"].to_list())
    keep = [r for r in revs if r["label"] and r["label"] != "[Admin1]"
            and r.get("diff_base_reason") != "earlier_revisions_not_published"
            and r["rev_id"] not in bc and not REDIR.match(r["body"] or "")
            and not (nohub and r["page_key"] == HUB) and not (drop and (r["body"] or "").startswith(drop))]
    df = pl.DataFrame({"rev": [r["rev_id"] for r in keep], "label": [r["label"] for r in keep],
                       "page": [r["page_key"] for r in keep], "ip16": [r["ip16"] for r in keep],
                       "t": [r["time"] for r in keep]})
    df = df.with_columns(pl.col("t").str.to_datetime("%Y-%m-%dT%H:%M:%SZ", time_zone="UTC"))
    return df.with_columns(pl.col("t").dt.epoch("s").alias("s"), pl.col("t").dt.strftime("%Y-%m-%d").alias("day")).sort("s")


def units(df, mode, starts):
    """List of (day, page|None, label, real_end, candidate_times[]) for each unit."""
    out = []
    if mode == "day":
        last = df.group_by("day").agg(pl.col("s").max().alias("T"), pl.col("s").min().alias("T0"))
        T = {d: (t0, t) for d, t, t0 in last.iter_rows()}
        for (day, lab), g in df.group_by(["day", "label"], maintain_order=True):
            s = g["s"].to_numpy(); t0, t = T[day]
            if starts:
                c = s[s <= t0 + HOUR]
                if len(c): out.append((day, None, lab, s.min(), c))
            else:
                c = s[s >= t - HOUR]
                if len(c): out.append((day, None, lab, s.max(), c))
        return out
    keys = ["label"] if mode == "session" else ["label", "page"]
    for k, g in df.group_by(keys, maintain_order=True):
        s = np.sort(g["s"].to_numpy()); cut = np.where(np.diff(s) >= GAP)[0]
        for seg in np.split(s, cut + 1):
            e = seg[0] if starts else seg[-1]
            c = seg[seg <= e + HOUR] if starts else seg[seg >= e - HOUR]
            day = str(np.datetime64(int(e), "s"))[:10]
            out.append((day, k[1] if mode == "page" else None, k[0], e, c))
    return out


def maxwin(t, w):
    if len(t) == 0: return 0, None
    t = np.sort(t); n = np.searchsorted(t, t + w, side="right") - np.arange(len(t)); i = int(n.argmax())
    return int(n[i]), int(t[i])


def stat(us, ends, w, groups=False):
    """per day: max over the day (session/day) or over pages (page) of units ending in a w-s window.
    groups=True returns the per-(day, page) values instead."""
    g = defaultdict(list)
    for u, e in zip(us, ends): g[(u[0], u[1])].append(e)
    per = {k: maxwin(np.array(es), w)[0] for k, es in g.items()}
    if groups: return per
    best = defaultdict(int)
    for (day, _), k in per.items(): best[day] = max(best[day], k)
    return best


def run(mode, n, nohub, starts, drop=None, informative=False):
    df = load(nohub, drop); us = units(df, mode, starts)
    if informative: us = [u for u in us if len(np.unique(u[4])) > 1]  # units the null can move
    rng = np.random.default_rng(0)
    real = {w: stat(us, [u[3] for u in us], w) for w in WS}
    realg = {w: stat(us, [u[3] for u in us], w, True) for w in WS}
    watch = [k for k in realg[10] if k[1] is not None and max(realg[w][k] for w in WS) >= 4]  # page mode: busy pages
    nulls = {w: defaultdict(list) for w in WS}
    nullg = {w: defaultdict(list) for w in WS}
    days = sorted(real[WS[0]])
    for _ in range(n):
        ends = [u[4][rng.integers(len(u[4]))] for u in us]
        for w in WS:
            st = stat(us, ends, w, True); best = defaultdict(int)
            for (d, _), k in st.items(): best[d] = max(best[d], k)
            for d in days: nulls[w][d].append(best.get(d, 0))
            for k in watch: nullg[w][k].append(st[k])
    res = {"mode": mode, "nohub": nohub, "starts": starts, "n": n, "units": len(us),
           "informative": sum(len(np.unique(u[4])) > 1 for u in us), "days": {}}
    for d in days:
        nd = sum(u[0] == d for u in us)
        res["days"][d] = {"units": nd, **{f"w{w}": {"real": real[w][d], "mean": float(np.mean(nulls[w][d])),
                          "p95": float(np.percentile(nulls[w][d], 95)),
                          "p": (1 + sum(x >= real[w][d] for x in nulls[w][d])) / (n + 1)} for w in WS}}
    pv = lambda r, xs: {"real": r, "mean": float(np.mean(xs)), "p95": float(np.percentile(xs, 95)),
                        "p": (1 + sum(x >= r for x in xs)) / (n + 1)}
    res["pages"] = {f"{d} {p}": {"units": sum(u[0] == d and u[1] == p for u in us),
                                 **{f"w{w}": pv(realg[w][(d, p)], nullg[w][(d, p)]) for w in WS}} for d, p in watch}
    # top real windows per w, with their members and each member's next save anywhere (for reading)
    tops, g = [], defaultdict(list)
    for u in us: g[(u[0], u[1])].append(u)
    nxt = {lab: gg["s"].to_numpy() for (lab,), gg in df.group_by(["label"])}
    for w in WS:
        for (day, page), uu in g.items():
            k, t0 = maxwin(np.array([u[3] for u in uu]), w)
            if k < 3 + (w > 10): continue
            mem = sorted((u for u in uu if t0 <= u[3] <= t0 + w), key=lambda u: u[3])
            saves = []
            for u in mem:
                r = df.filter((pl.col("label") == u[2]) & (pl.col("s") == int(u[3])) & ((pl.col("page") == page) if page else True)).row(0, named=True)
                ns = nxt[u[2]][nxt[u[2]] > u[3]] if not (starts) else nxt[u[2]][nxt[u[2]] < u[3]]
                saves.append([r["t"].strftime("%H:%M:%S"), u[2], r["page"], r["rev"], r["ip16"],
                              str(np.datetime64(int(ns[0] if not starts else ns[-1]), "s")) if len(ns) else None])
            ips = [x[4] for x in saves]
            tops.append({"ip16_distinct": len(set(ips)), "w": w, "day": day, "page": page, "k": k, "t0": str(np.datetime64(t0, "s")), "saves": saves})
    res["tops"] = sorted(tops, key=lambda x: (x["w"], -x["k"]))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--mode", default="all")
    ap.add_argument("--nohub", action="store_true")
    ap.add_argument("--starts", action="store_true")
    ap.add_argument("--informative", action="store_true", help="only units with >= 2 distinct save times in the hour")
    ap.add_argument("--drop", default=None, help="drop saves whose body starts with this (e.g. '= DZFASTMD')")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    for m in (["day", "session", "page"] if a.mode == "all" else [a.mode]):
        r = run(m, a.n, a.nohub, a.starts, a.drop, a.informative)
        tag = m + ("_nohub" if a.nohub else "") + ("_starts" if a.starts else "") + ("_inf" if a.informative else "") \
            + ("_nodz" if a.drop else "")
        json.dump(r, open(f"{OUT}/c32_{tag}.json", "w"), indent=1, default=str)
        print(tag, "units", r["units"], "informative", r["informative"])
        for d, v in list(r["days"].items()) + [("PAGE " + k, v) for k, v in r.get("pages", {}).items()]:
            if v["units"] >= 5:
                print(" ", d, v["units"], *(f"w{w} {v[f'w{w}']['real']} ({v[f'w{w}']['mean']:.1f}/{v[f'w{w}']['p95']:.0f} p={v[f'w{w}']['p']:.3f})" for w in WS))
