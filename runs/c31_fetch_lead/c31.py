"""C31: fetch first, post later — does urlquery's first scan of a data-source family precede the wiki's first post of
that family on the same day, more often and by more hours than chance?
Unit: (family, day) with >=1 included urlquery report of the family and >=1 wiki add mentioning it that day.
lead = first wiki add - first urlquery scan (hours; > 0 = urlquery first). Statistics: share urlquery-first, median lead;
alt: median wiki time - median scan time of the pair (robust to one early row). Coupling, not order: median |lead|
(lower tail: closer than chance).
Nulls (day = stratum, the whole comparison unit): N1 family labels of urlquery rows permuted among ALL included urlquery
rows of that day (keeps the scanner's daily rhythm and the per-day counts); N2 the same on the wiki side (family-label
sets of all wiki adds of that day); N3 the family's scans circularly shifted by U(0, 24 h) inside the day.
Families: data_source (urlquery) as in prepare/uq_wiki.py plus four sources found by URL in wiki text; wiki side is
multi-label (page family prefix, plus every keyword hit).
usage (repo root): REPO=. python runs/c31_fetch_lead/c31.py [--n 2000] [--offset-h 0] [--wiki msgs|records] [--pairs out.csv]"""
import argparse, os, re
import numpy as np, polars as pl

R = os.environ.get("REPO", ".") + "/"
SRC = {"SEC county data": "sec-county", "AIHW": "aihw", "IHME": "ihme", "DataUSA": "datausa", "MAX budget documents": "max-budget",
       "Maryland school report cards": "maryland-schools", "UNM digital library": "unm-library", "UNCTAD": "unctad",
       "Thrill Data": "thrill-data", "USAspending": "usaspending", "Clark economics newsletter": "clark-econ",
       "Digital Public Library of America": "dpla", "US Census API": "us-census"}
ORIGINAL = {"sec-county", "aihw", "ihme", "datausa", "max-budget", "maryland-schools", "unm-library", "unctad", "thrill-data"}
KW = [("sec-county", r"sec\.gov/files/county|county\.json"), ("max-budget", r"max\.gov|max\.omb\.gov"), ("maryland-schools", r"maryland"),
      ("unm-library", r"unm\.edu|digitalrepository\.unm"), ("aihw", r"aihw"), ("ihme", r"ihme|healthdata\.org"), ("datausa", r"datausa"),
      ("unctad", r"unctad"), ("thrill-data", r"thrill"), ("usaspending", r"usaspending"), ("clark-econ", r"clarku"),
      ("dpla", r"\bdp\.la\b"), ("us-census", r"census\.gov")]
H = 3600e6  # microseconds per hour


def wiki_fams(page_family, text):
    fs = {f for p, f in (("aihw", "aihw"), ("ihme", "ihme"), ("datausa", "datausa")) if (page_family or "").startswith(p)}
    t = (text or "").lower()
    return sorted(fs | {f for f, rx in KW if re.search(rx, t)})


def load(wiki_src, offset_h):
    u = pl.read_parquet(R + "data/transluce/urlquery.parquet").filter(pl.col("disposition") == "included")
    u = u.select("id", "time", pl.col("data_source").replace_strict(SRC, default=None).alias("fam"))
    u = u.with_columns(pl.col("fam").map_elements(lambda f: [f], return_dtype=pl.List(pl.Utf8)).fill_null([]).alias("fams"))
    if wiki_src == "msgs":
        w = pl.read_parquet(R + "data/wiki_msgs.parquet").filter(pl.col("kind") == "add").select("id", "time", "page", "label", "page_family", "text")
    else:  # records: distinct wiki messages at first appearance (prepare/uq_wiki.py)
        w = pl.read_parquet(R + "data/uq_wiki_union.parquet").filter(pl.col("source") == "wiki").select("id", "time", "page", pl.lit(None, pl.Utf8).alias("label"), "page_family", "text")
    w = w.with_columns(pl.struct("page_family", "text").map_elements(lambda r: wiki_fams(r["page_family"], r["text"]), return_dtype=pl.List(pl.Utf8)).alias("fams"))
    day = lambda d: d.with_columns((pl.col("time") - pl.duration(hours=offset_h)).dt.date().alias("day"), pl.col("time").dt.epoch("us").alias("us"))
    return day(u), day(w)


def strata(df, days):
    """per day: sorted times (us) and, per family, the row indices carrying it"""
    out = {}
    for (d,), g in df.filter(pl.col("day").is_in(list(days))).sort("time").group_by(["day"], maintain_order=True):
        idx = {}
        for i, fs in enumerate(g["fams"].to_list()):
            for f in fs:
                idx.setdefault(f, []).append(i)
        out[d] = (g["us"].to_numpy(), {f: np.array(v) for f, v in idx.items()}, g)
    return out


def firsts(st, pairs, perm_rng=None, circ_rng=None, offset_h=0):
    """first and median time per pair; optionally after permuting labels within the day or circular shifting"""
    first, med = np.empty(len(pairs)), np.empty(len(pairs))
    perms = {d: perm_rng.permutation(len(st[d][0])) for d in sorted({d for _, d in pairs})} if perm_rng is not None else {}
    for k, (f, d) in enumerate(pairs):
        t, idx, _ = st[d]
        x = t[perms[d][idx[f]]] if perms else t[idx[f]]
        if circ_rng is not None:
            d0 = np.datetime64(d, "us").astype(np.int64) + offset_h * H
            x = d0 + (x - d0 + circ_rng.uniform(0, 24 * H)) % (24 * H)
        first[k], med[k] = x.min(), np.median(x)
    return first, med


def stats(uf, wf, um, wm, sel):
    lead, mlead = (wf - uf)[sel] / H, (wm - um)[sel] / H
    return np.array([(lead > 0).mean(), np.median(lead), (mlead > 0).mean(), np.median(mlead), np.median(np.abs(lead))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2000); ap.add_argument("--offset-h", type=int, default=0)
    ap.add_argument("--wiki", default="msgs"); ap.add_argument("--pairs", default=None); ap.add_argument("--seed", type=int, default=31)
    a = ap.parse_args()
    u, w = load(a.wiki, a.offset_h)
    ku = u.explode("fams", empty_as_null=True).drop_nulls("fams").select("fams", "day").unique()
    kw = w.explode("fams", empty_as_null=True).drop_nulls("fams").select("fams", "day").unique()
    pairs = [(f, d) for f, d in ku.join(kw, on=["fams", "day"]).sort("fams", "day").iter_rows()]
    days = {d for _, d in pairs}
    su, sw = strata(u, days), strata(w, days)
    uf, um = firsts(su, pairs); wf, wm = firsts(sw, pairs)
    fam = np.array([f for f, _ in pairs])
    first_day = {}
    for i, (f, d) in enumerate(pairs):
        first_day.setdefault(f, i)
    later = np.ones(len(pairs), bool); later[list(first_day.values())] = False
    nu, nw = (np.array([len(st[d][1][f]) for f, d in pairs]) for st in (su, sw))
    sels = {"all": np.ones(len(pairs), bool), "later days": later, "original map": np.isin(fam, list(ORIGINAL)), ">=3 rows each": (nu >= 3) & (nw >= 3),
            **{f"drop {f}": fam != f for f in sorted(set(fam))}, **{f"only {f}": fam == f for f in sorted(set(fam))}}
    real = {k: stats(uf, wf, um, wm, s) for k, s in sels.items() if s.any()}
    rng = np.random.default_rng(a.seed)
    nulls = {k: {n: [] for n in real} for k in ("N1 uq-perm", "N2 wiki-perm", "N3 uq-circ")}
    for _ in range(a.n):
        draws = {"N1 uq-perm": (firsts(su, pairs, perm_rng=rng), (wf, wm)), "N2 wiki-perm": ((uf, um), firsts(sw, pairs, perm_rng=rng)),
                 "N3 uq-circ": (firsts(su, pairs, circ_rng=rng, offset_h=a.offset_h), (wf, wm))}
        for k, ((nuf, num), (nwf, nwm)) in draws.items():
            for n, s in sels.items():
                if n in real:
                    nulls[k][n].append(stats(nuf, nwf, num, nwm, s))
    print(f"C31  wiki={a.wiki}  day boundary {a.offset_h:02d}:00 UTC  pairs={len(pairs)}  families={len(set(fam))}  null n={a.n}")
    names = ["share uq-first", "median lead h", "share med-uq-first", "median med-lead h", "median |lead| h (low)"]
    for n, r in real.items():
        if not (n in ("all", "later days", "original map", ">=3 rows each") or n.startswith("drop")):
            continue
        print(f"\n[{n}] pairs={sels[n].sum()}")
        for j, s in enumerate(names):
            line = f"  {s:20s} real {r[j]:7.2f} |"
            for k in nulls:
                v = np.array(nulls[k][n])[:, j]
                hit, q = ((v <= r[j]), 5) if j == 4 else ((v >= r[j]), 95)
                line += f" {k}: mean {np.nanmean(v):6.2f} p{q} {np.nanpercentile(v, q):6.2f} p {(1 + hit.sum()) / (1 + len(v)):.4f} |"
            print(line)
    print("\nper family: pairs | uq-first | median lead h | N1 mean share, p | N2 mean share, p")
    for f in sorted(set(fam)):
        n, r = f"only {f}", real[f"only {f}"]
        v1, v2 = np.array(nulls["N1 uq-perm"][n])[:, 0], np.array(nulls["N2 wiki-perm"][n])[:, 0]
        k = sels[n].sum()
        print(f"  {f:16s} {k:3d} | {round(r[0] * k):3d} | {r[1]:7.2f} | {v1.mean():.2f}, {(1 + (v1 >= r[0]).sum()) / (1 + len(v1)):.4f} | {v2.mean():.2f}, {(1 + (v2 >= r[0]).sum()) / (1 + len(v2)):.4f}")
    rows = []
    for k, (f, d) in enumerate(pairs):
        gu, gw = su[d][2], sw[d][2]
        iu, iw = int(su[d][1][f][0]), int(sw[d][1][f][0])
        rows.append({"family": f, "day": str(d), "n_uq": len(su[d][1][f]), "n_wiki": len(sw[d][1][f]), "lead_h": round((wf[k] - uf[k]) / H, 2),
                     "med_lead_h": round((wm[k] - um[k]) / H, 2), "uq_before_wiki": int((su[d][0][su[d][1][f]] < wf[k]).sum()),
                     "uq_first": gu["time"][iu].strftime("%H:%M:%S"), "uq_id": gu["id"][iu], "wiki_first": gw["time"][iw].strftime("%H:%M:%S"),
                     "wiki_id": gw["id"][iw], "page": gw["page"][iw], "label": gw["label"][iw], "later_day": bool(later[k])})
    pt = pl.DataFrame(rows)
    pl.Config.set_tbl_rows(100); pl.Config.set_tbl_cols(20); pl.Config.set_fmt_str_lengths(48); pl.Config.set_tbl_width_chars(250)
    print(pt.drop("uq_id", "wiki_id"))
    if a.pairs:
        pt.write_csv(a.pairs)


if __name__ == "__main__":
    main()
