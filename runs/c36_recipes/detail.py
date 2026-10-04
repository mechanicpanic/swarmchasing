"""C36 details on the units written by c36.py: (1) for first uses that saw the recipe on the page, how long before
another label had put it there and whether the focal save repeats one of those lines verbatim (a copy) or wraps a
different URL in the same recipe; (2) each recipe's very first users (first unit and first add anywhere): page new?
label's first save? what else that save carried; (3) per recipe: share of first uses made in the label's first save
and on a page birth.
usage (repo root): REPO=. OUT=... python runs/c36_recipes/detail.py [--nohub]"""
import argparse, os
import polars as pl
from common import CRE, RECIPES, line_owners, load_adds, load_revs

OUT = os.environ.get("OUT", "results/c36_recipes")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--nohub", action="store_true"); a = ap.parse_args()
    sfx = "_nohub" if a.nohub else ""
    u = pl.read_parquet(f"{OUT}/c36_units{sfx}.parquet")
    revs, adds = load_revs(), load_adds()
    owners = line_owners(revs)
    t_of = dict(revs.select("rev", "s").iter_rows())
    added_lines = {r: {x.strip() for x in t.split("\n") if x.strip()} for r, t in
                   adds.group_by("rev").agg(pl.col("text").str.join("\n")).iter_rows()}
    # edit summary of the source save (digits removed) equal to the focal save's: one script under two labels (S12)
    # when did another label last insert a matching line on that page (from the adds)
    addm = adds.select("rev", "label", "page", pl.col("time").dt.epoch("s").alias("s"), "text")
    summ = dict(revs.select("rev", pl.col("summary").fill_null("").str.replace_all(r"[\d.]+", "#").str.strip_chars()).iter_rows())
    rows = []
    for r in u.filter(pl.col("page_vis")).iter_rows(named=True):
        k = r["recipe"]; c = CRE[k]; t = t_of[r["rev"]]
        vis = {x for x, o in owners[r["prev_rev"]] if c.search(x) and o != r["label"]}
        mine = {x for x in added_lines.get(r["rev"], ()) if c.search(x)}
        prev_add = addm.filter((pl.col("page") == r["page"]) & (pl.col("label") != r["label"]) & (pl.col("s") < t)
                               & pl.col("text").str.contains(RECIPES[k]))
        lag = t - prev_add["s"].max() if prev_add.height else None
        src = prev_add.sort("s")["rev"][-1] if prev_add.height else None
        same_sum = bool(src) and summ.get(src) == summ.get(r["rev"]) and summ.get(src) not in ("", "*", "#")
        rows.append({"recipe": k, "rev": r["rev"], "verbatim": bool(vis & mine), "lag_s": lag, "same_summary": same_sum})
    d = pl.DataFrame(rows)
    print("== first uses that saw the recipe on the page: lag since another label's last add there; verbatim line copy; same edit summary (digits removed, not empty/'*') as that add")
    print(d.group_by("recipe").agg(pl.len().alias("n"), pl.col("verbatim").sum().alias("verbatim"),
                                   pl.col("lag_s").median().alias("lag_med_s"), (pl.col("lag_s") <= 30).sum().alias("lag<=30s"),
                                   (pl.col("lag_s") > 600).sum().alias("lag>10min"),
                                   pl.col("same_summary").sum().alias("same_summary")).sort("n", descending=True))
    tot = d.select(pl.len(), pl.col("verbatim").sum(), (pl.col("lag_s") <= 30).sum().alias("le30"), pl.col("lag_s").median().alias("med"), (pl.col("lag_s") > 600).sum().alias("gt600"), pl.col("same_summary").sum().alias("same_sum"))
    print("all:", tot.row(0))
    print("\n== per recipe: units, first-use in label's first save, on a page birth, page-visible")
    print(u.group_by("recipe", maintain_order=True).agg(pl.len().alias("n"), pl.col("first_save").sum(), pl.col("new_page").sum(),
                                                        pl.col("page_vis").sum(), pl.col("page10").sum()))
    print("\n== very first users (rank 0 unit) and first add anywhere (any label, any revision)")
    for k in RECIPES:
        x = u.filter((pl.col("recipe") == k) & (pl.col("rank") == 0))
        if x.height == 0: continue
        r = x.row(0, named=True)
        fa = addm.filter(pl.col("text").str.contains(RECIPES[k])).sort("s").head(1).row(0, named=True)
        other = [kk for kk, cc in CRE.items() if kk != k and cc.search(r["added"])]
        print(f"{k:26s} {r['t']} {r['label']:24s} {r['rev']:45s} new_page={r['new_page']} first_save={r['first_save']} "
              f"summary={r['summary']!r} | first add anywhere: {fa['rev']} {fa['label']!r} | also in that save: {other}")
    # body variant test for the one-page templates: is the label's first template body (digits removed) the same
    # variant as the template body standing most recently before it, more than as a random earlier template body?
    print("\n== template variants: first body equals the most recent earlier variant by another label vs any earlier one")
    for k in [k for k in RECIPES if k.startswith("= ")]:
        sv = revs.filter(pl.col("body").str.contains(RECIPES[k])).select("rev", "label", "s",
                                                                          pl.col("body").str.replace_all(r"\d+", "#").alias("v")).sort("s")
        fu = u.filter(pl.col("recipe") == k)["rev"].to_list()
        hit = base = loc = n = 0
        for rv in fu:
            row = sv.filter(pl.col("rev") == rv)
            if row.height == 0: continue
            v, lab, s = row["v"][0], row["label"][0], row["s"][0]
            prev = sv.filter((pl.col("s") < s) & (pl.col("label") != lab))
            if prev.height == 0: continue
            n += 1; hit += prev["v"][-1] == v; base += float((prev["v"] == v).mean())
            near = prev.filter(pl.col("s") >= s - 600); loc += float((near["v"] == v).mean()) if near.height else 0.0
        if n: print(f"{k:26s} units with an earlier copy {n}: same variant as latest {hit} ({hit / n:.2f}); "
                    f"expected if drawn from earlier copies {base:.1f} ({base / n:.2f}), from copies of the last 10 min {loc:.1f} ({loc / n:.2f}); variants {sv['v'].n_unique()} in {sv.height} bodies")


if __name__ == "__main__":
    main()
