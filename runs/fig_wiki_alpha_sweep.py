"""Figure: admin deletion sweeps against alphabetical page-name rank (the four largest sweeps).
Sweeps as in runs/deletion_order.py (branch docs/dsewiki-report): RUN(field(kind, delete)){10,400} DURING 10 minutes
= runs of deletes with no gap over 10 minutes, 10 to 400 deletes; names ASCII-sorted, wiki prefix dropped.
Numbers asserted below come from notes/2026-10-03-dsewiki-report.md section 5.
uv run --with matplotlib --with polars python runs/fig_wiki_alpha_sweep.py   -> report/figures/wiki_alpha_sweep.png"""
from collections import defaultdict
from pathlib import Path
import polars as pl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT = Path(__file__).resolve().parent.parent
def data_path(name):  # worktrees may carry a broken data/ link: fall back to the main checkout
    for base in (ROOT, *ROOT.parents):
        p = base / "data" / name
        if p.is_file(): return p
    raise SystemExit(f"{name} not found under any data/")
d = (pl.read_parquet(data_path("wiki_msgs.parquet"), columns=["time", "seq", "page", "kind"])
       .filter(pl.col("kind") == "delete").sort("time", "seq"))
times = d["time"].to_list(); names = [p.split("~", 1)[1] for p in d["page"]]

runs, cur = [], [0]
for i in range(1, len(times)):
    if (times[i] - times[i - 1]).total_seconds() <= 600: cur.append(i)
    else: runs.append(cur); cur = [i]
runs.append(cur)
sweeps = [r for r in runs if 10 <= len(r) <= 400]
asc = lambda ns: sum(x <= y for x, y in zip(ns, ns[1:]))

# ---- checks against the notes (section 5) ----
assert d.height == 5217, d.height                                       # "5,217 deletions"
assert len(sweeps) == 108 and sum(map(len, sweeps)) == 5084, (len(sweeps), sum(map(len, sweeps)))  # "108 sweeps, 5,084 of the 5,217"
per = defaultdict(lambda: [0, 0]); day = defaultdict(lambda: [0, 0])
for r in sweeps:
    ns = [names[i] for i in r]; s = str(times[r[0]])[:10]
    k = "Jun 18-20" if s <= "2026-06-20" else ("Jul 12-14" if s >= "2026-07-12" else "Jun 22-Jul 11")
    per[k][0] += asc(ns); per[k][1] += len(ns) - 1
    day[s][0] += asc(ns); day[s][1] += len(ns) - 1
for k, (pairs, share) in {"Jun 18-20": (404, .775), "Jun 22-Jul 11": (3700, .521), "Jul 12-14": (872, .922)}.items():
    assert per[k][1] == pairs and round(per[k][0] / per[k][1], 3) == share, (k, per[k])   # table of section 5
for s, share in {"2026-06-19": .818, "2026-07-13": .982, "2026-07-14": .993}.items():
    assert round(day[s][0] / day[s][1], 3) == share, (s, day[s])        # "Jun 19 0.818 ... Jul 13 0.982 ... Jul 14 0.993"

# ---- plot: the four largest sweeps, in time order ----
big = sorted(sorted(sweeps, key=len, reverse=True)[:4], key=lambda r: times[r[0]])
fig, axs = plt.subplots(2, 2, figsize=(10, 7))
for ax, r in zip(axs.flat, big):
    ns = [names[i] for i in r]; ts = [times[i] for i in r]
    order = sorted(ns); rank = {n: order.index(n) + 1 for n in order}   # ties share the lowest rank
    ax.scatter(ts, [rank[n] for n in ns], s=9, color="#0072B2", linewidths=0)
    share = asc(ns) / (len(ns) - 1)
    ax.set_title(f"{ts[0]:%b %d}: {len(ns)} deletions, {share:.0%} of consecutive pairs ascend", fontsize=9.5, loc="left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.set_xlabel(f"Time of deletion, {ts[0]:%b %d} (UTC)", fontsize=9)
    ax.set_ylabel("Alphabetical rank of page name\nwithin this sweep (1 = first)", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False); ax.tick_params(labelsize=8)
fig.suptitle("Order of the admin's page deletions in the four largest sweeps, against alphabetical page-name rank",
             fontsize=11, x=0.02, ha="left")
fig.tight_layout(rect=(0, 0, 1, 0.96))
out = ROOT / "report" / "figures" / "wiki_alpha_sweep.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=150)
print("wrote", out)
for r in big:
    ns = [names[i] for i in r]; print(times[r[0]], len(ns), round(asc(ns) / (len(ns) - 1), 3))
