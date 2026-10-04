# Change-point detection on weekly per-agent feature series (weekly.parquet).
# Method: binary segmentation with a two-segment mean split (max SSE reduction),
# up to depth 2. A split is flagged when:
#   - effect size d = |mean_after - mean_before| / max(pooled within-seg sd, floor) >= 1.5
#     (floor = 0.25 x the feature's cross-agent sd of weekly values, so near-constant
#     series don't explode)
#   - permutation p (499 shuffles of the max-SSE-reduction statistic) <= 0.01
#   - abrupt, not a drift: step SSE <= 0.8 x linear-trend SSE on the same segment,
#     and the 2-week-before vs 2-week-after jump carries >= 50% of the shift.
# Weeks with fewer than MIN_N messages/thoughts/actions are dropped.
import numpy as np, polars as pl

OUT = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/leads-changepoints/"
MIN_N, MIN_WEEKS, MIN_SEG = 10, 8, 3
rng = np.random.default_rng(0)
w = pl.read_parquet(OUT + "weekly.parquet").filter(pl.col("value").is_not_null() & (pl.col("n") >= MIN_N))
floor = w.group_by("feature").agg((pl.col("value").std() * 0.25).alias("floor"))
fl = dict(floor.iter_rows())


def best_split(x):
    n = len(x); cs = np.cumsum(x); cs2 = np.cumsum(x * x); tot = cs[-1]; tot2 = cs2[-1]
    sse_all = tot2 - tot * tot / n
    k = np.arange(MIN_SEG, n - MIN_SEG + 1)
    l1 = cs[k - 1]; l2 = cs2[k - 1]
    sse = (l2 - l1 * l1 / k) + ((tot2 - l2) - (tot - l1) ** 2 / (n - k))
    i = np.argmin(sse)
    return int(k[i]), sse_all - sse[i], sse[i]


def perm_p(x, stat, B=499):
    c = 0
    for _ in range(B):
        if best_split(rng.permutation(x))[1] >= stat: c += 1
    return (c + 1) / (B + 1)


def lin_sse(x):
    t = np.arange(len(x)); A = np.vstack([t, np.ones_like(t)]).T
    r = np.linalg.lstsq(A, x, rcond=None)[1]
    return float(r[0]) if len(r) else 0.0


def segment(x, weeks, lo, hi, feat, depth, out):
    seg = x[lo:hi]
    if len(seg) < 2 * MIN_SEG or depth > 2: return
    k, gain, sse = best_split(seg)
    a, b = seg[:k], seg[k:]
    sd = np.sqrt(((a - a.mean()) ** 2).sum() + ((b - b.mean()) ** 2).sum()) / np.sqrt(max(len(seg) - 2, 1))
    d = abs(b.mean() - a.mean()) / max(sd, fl[feat], 1e-9)
    if d < 1.5: return
    p = perm_p(seg, gain)
    jump = b[:2].mean() - a[-2:].mean()
    abrupt = (sse <= 0.8 * lin_sse(seg)) and (np.sign(jump) == np.sign(b.mean() - a.mean())) and abs(jump) >= 0.5 * abs(b.mean() - a.mean())
    if p <= 0.01:
        out.append(dict(week=weeks[lo + k], prev_week=weeks[lo + k - 1], before=float(a.mean()), after=float(b.mean()),
                        local_before=float(a[-4:].mean()), local_after=float(b[:4].mean()),
                        d=float(d), p=p, abrupt=bool(abrupt), depth=depth,
                        seg_start=weeks[lo], seg_end=weeks[hi - 1], n_weeks_before=len(a), n_weeks_after=len(b)))
        segment(x, weeks, lo, lo + k, feat, depth + 1, out)
        segment(x, weeks, lo + k, hi, feat, depth + 1, out)


rows = []
first = w.group_by("agent").agg(pl.col("week").min().alias("first_week"), pl.col("week").max().alias("last_week"))
for (agent, feat, src), g in w.sort("week").group_by(["agent", "feature", "src"], maintain_order=True):
    if g.height < MIN_WEEKS: continue
    x = g["value"].to_numpy().astype(float); weeks = g["week"].to_list()
    if np.nanstd(x) == 0: continue
    out = []
    segment(x, weeks, 0, len(x), feat, 0, out)
    for o in out: rows.append(dict(agent=agent, feature=feat, src=src, **o))

cp = pl.DataFrame(rows).join(first, on="agent").with_columns(
    ((pl.col("week") - pl.col("first_week")).dt.total_days() // 7).alias("weeks_since_first"),
    ((pl.col("after") - pl.col("before")).sign()).alias("direction"))
cp.write_parquet(OUT + "changepoints_raw.parquet")
print(cp.height, "flags;", cp.filter("abrupt").height, "abrupt")
