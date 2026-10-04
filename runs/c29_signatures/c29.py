"""C29 (report §12): multi-label signatures in wiki_msgs: authorship (first appearance of a signed line), sessions, concurrency, runs vs a shuffled-signer null; labels.py: own / self-made / borrowed labels; classify.py: rotation / mixed / shared. usage (repo root): uv run python runs/c29_signatures/c29.py <outdir>; WIKI_MSGS overrides the data path."""
"""C29: signatures added under >=5 labels -- one runtime rotating labels, or several runs sharing a name?
Signed save = a revision whose ADDED text (kind=add hunks) carries a signature '-- Name' more times than its removed
text does (net add; an edited signed line appears in both and is not a new signature).
"""
import re, sys, collections
import numpy as np, polars as pl

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
D = pl.read_parquet(__import__("os").environ.get("WIKI_MSGS", "data/wiki_msgs.parquet"))
R = re.compile(r"--\s*\[?\[?([A-Z][A-Za-z0-9]{3,40})")
rng = np.random.default_rng(29)
NPERM = 1000

# ---- signed messages: one unit per signature on a line (text since the previous signature on that line, or the
# line start; a bare '-- Name' line takes the previous non-empty line too). A unit is AUTHORED at its first appearance
# anywhere in the stream (normalised text); later appearances are copies/restores (readd, relay) and are not authorship.
adds = D.filter(pl.col("kind") == "add").sort("seq", "hunk")
seen = {}; saves = []; raw = collections.defaultdict(set); copies = collections.Counter(); copy_other = collections.Counter()
norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())  # ASCII alnum only: mojibake from re-saves and spacing do not make a copy new
for r in adds.iter_rows(named=True):
    lines = (r["text"] or "").split("\n")
    for li, line in enumerate(lines):
        pos = 0
        for m in R.finditer(line):
            s = m.group(1); raw[s].add(r["label"])
            body = line[pos:m.end()]
            if len(line[pos:m.start()].strip()) < 15:
                prev = next((x for x in reversed(lines[:li]) if x.strip()), "")
                body = prev + " " + body
            pos = m.end(); k = norm(body)
            if k in seen:
                copies[s] += 1; copy_other[s] += seen[k] != r["label"]
                continue
            seen[k] = r["label"]
            saves.append(dict(rev=r["rev"], sig=s, time=r["time"], seq=r["seq"], page=r["page"], label=r["label"],
                              ip16=r["ip16"], add_type=r["add_type"], text_key=k[:200]))
S = pl.DataFrame(saves).sort("seq")
S = S.unique(["rev", "sig"], keep="first").sort("seq")
nl = S.group_by("sig").agg(pl.col("label").n_unique().alias("labels"))
print(f"signers (authored units): {S['sig'].n_unique()}; >=5 labels: {nl.filter(pl.col('labels') >= 5).height}; "
      f"raw hunk adds: {len(raw)} signers, >=5 labels {sum(len(v) >= 5 for v in raw.values())}")
targets = nl.filter(pl.col("labels") >= 5)["sig"].to_list()

# signed-save stream: one entry per rev with the set of its net-added signatures
st = S.group_by("rev").agg(pl.col("sig"), pl.col("seq").first(), pl.col("time").first(), pl.col("page").first(),
                          pl.col("label").first()).sort("seq")
st = st.with_columns(pl.col("time").dt.date().alias("day"))
all_sigs = set(S["sig"].unique())
TS = re.compile(r"\d{9,}$")


def runs(x):
    x = np.asarray(x, bool)
    return int(x[0]) + int(np.sum(x[1:] & ~x[:-1])) if len(x) else 0


res = []
for sig in targets:
    s = S.filter(pl.col("sig") == sig).sort("seq")
    t = s["time"].to_numpy().astype("datetime64[s]").astype(np.int64)
    gaps = np.diff(t)
    sess = np.concatenate([[0], np.cumsum(gaps > 600)])
    s = s.with_columns(pl.Series("sess", sess))
    per = s.group_by("sess", maintain_order=True).agg(pl.len().alias("n"), pl.col("label").n_unique().alias("nl"),
                                                       pl.col("ip16").n_unique().alias("nip"), pl.col("label").alias("labs"),
                                                       pl.col("page").n_unique().alias("np"), pl.col("time").min().alias("t0"),
                                                       pl.col("time").max().alias("t1"), pl.col("seq").min().alias("q0"),
                                                       pl.col("seq").max().alias("q1"))
    every = all(all(a != b for a, b in zip(l[:-1], l[1:])) for l in per["labs"].to_list() if len(l) > 1)
    multi = per.filter(pl.col("n") > 1)
    # concurrency: two saves, different labels, different pages, within 1 s / 60 s
    lab = s["label"].to_list(); pg = s["page"].to_list()
    c1 = c60 = 0
    for i in range(len(t)):
        for j in range(i + 1, len(t)):
            if t[j] - t[i] > 60: break
            if lab[i] != lab[j] and pg[i] != pg[j]:
                c60 += 1; c1 += (t[j] - t[i]) <= 1
    # stream on its pages; interleaving inside sessions; runs test with (day, page) shuffle
    pages = set(s["page"])
    sub = st.filter(pl.col("page").is_in(list(pages)))
    is_s = np.array([sig in x for x in sub["sig"].to_list()])
    others = [set(x) - {sig} for x in sub["sig"].to_list()]
    q = sub["seq"].to_numpy()
    inter_sess = 0; inter_saves = 0; other_signers = set()
    for q0, q1 in zip(per["q0"], per["q1"]):
        w = (q > q0) & (q < q1) & ~is_s
        if w.any():
            inter_sess += 1; inter_saves += int(w.sum())
            for k in np.where(w)[0]: other_signers |= others[k]
    real = runs(is_s)
    cells = sub.with_row_index("i").group_by("day", "page").agg(pl.col("i")).get_column("i").to_list()
    cells = [np.asarray(c) for c in cells if len(c) > 1]
    mixed_cells = sum(1 for c in cells if 0 < is_s[c].sum() < len(c))
    null = np.empty(NPERM, int)
    for k in range(NPERM):
        y = is_s.copy()
        for c in cells:
            y[c] = y[rng.permutation(c)]
        null[k] = runs(y)
    p_low = (np.sum(null <= real) + 1) / (NPERM + 1)
    labs = s["label"].to_list()
    own = sum(l == sig for l in labs); ts = sum(bool(TS.search(l or "")) for l in labs)
    other_sig_label = sum(l in all_sigs and l != sig for l in labs)
    res.append(dict(sig=sig, labels=s["label"].n_unique(), saves=s.height, pages=len(pages), ip16=s["ip16"].n_unique(),
                    days=s["time"].dt.date().n_unique(), sessions=per.height,
                    max_labels_in_session=int(per["nl"].max()), multi_sessions=multi.height,
                    multi_label_sessions=int((per["nl"] > 1).sum()), label_changes_every_save=every,
                    conc_1s=c1, conc_60s=c60, interleaved_sessions=inter_sess, interleaving_saves=inter_saves,
                    interleaving_signers=len(other_signers), stream=len(is_s), runs_real=real,
                    runs_null_mean=round(float(null.mean()), 1), runs_null_p5=int(np.percentile(null, 5)),
                    p_fewer=round(float(p_low), 3), p_more=round(float((np.sum(null >= real) + 1) / (NPERM + 1)), 3), informative_cells=mixed_cells,
                    own_label=own, ts_labels=ts, other_signer_labels=other_sig_label,
                    copies=copies[sig], copies_other_label=copy_other[sig],
                    distinct_texts=s["text_key"].n_unique(),
                    first=str(s["time"][0])[:19], last=str(s["time"][-1])[:19],
                    ids=s["rev"].to_list()))
R_ = pl.DataFrame(res).sort("labels", "saves", descending=True)
R_.write_parquet(f"{OUT}/c29_signatures.parquet")
S.write_parquet(f"{OUT}/c29_authored.parquet")
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(400)
R_.drop("ids").write_csv(f"{OUT}/c29_signatures.csv")
