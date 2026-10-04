"""The 311-page burst of 18 June (Mermachine's notes/2026-10-04-wiki-june18.md): page number against time, coloured by
writer name. Asserts the note's numbers before drawing.
usage: uv run --no-project --with matplotlib --with polars python runs/fig_broadcast.py -> report/figures/broadcast.png"""
import re
from pathlib import Path
import matplotlib.pyplot as plt
import polars as pl

D = next(p for p in [Path("data/wiki_msgs.parquet"), *[q / "data/wiki_msgs.parquet" for q in Path.cwd().parents]] if p.exists())
f = pl.read_parquet(D)
burst = f.filter((pl.col("text_key") == "146d7f0c0cfc7856") & (pl.col("kind") == "add")).sort("time")
assert burst.height == 314 and burst["page"].n_unique() == 314                      # "deleted all 314"
loop = burst.filter(pl.col("page").str.contains("~LoopNextWord"))
assert loop.height == 311                                                            # "311 new pages"
t0 = loop["time"].min()
secs = [(t - t0).total_seconds() for t in loop["time"]]
assert secs[-1] == 39                                                                # "in 39 s" (20:09:40-20:10:19)
num = [int(re.search(r"LoopNextWord(\d+)$", p).group(1)) for p in loop["page"]]
ks = {(n - 100000) // 20 for n in num}
assert all((n - 100000) % 20 in (0, 1) for n in num) and min(ks) == 130 and max(ks) == 300  # 100000+20k+{0,1}, k=130..300
assert burst["label"].n_unique() == 58                                              # "58 labels"
assert loop["label"][0] == "Agent0AddJS" and (burst["label"] == "Agent0AddJS").sum() == 46  # first save and 46 of them
rank = pl.DataFrame({"s": secs, "n": num}).select(pl.corr("s", "n", method="spearman")).item()
assert round(rank, 3) >= 0.999                                                       # "Spearman 0.999" (time in whole seconds: ties)
dels = f.filter((pl.col("kind") == "delete") & pl.col("page").is_in(burst["page"].implode()))
assert dels["page"].n_unique() == 314                                                # the admin deleted every one
again = f.filter(pl.col("page").is_in(burst["page"].implode()) & (pl.col("kind") == "add") & (pl.col("text_key") != "146d7f0c0cfc7856"))
assert again["page"].unique().to_list() == ["dse~CachePokeWord880000"] and again.height == 3  # the 311 Loop pages: never again

top = loop["label"].value_counts(sort=True).head(5)["label"].to_list()
fig, ax = plt.subplots(figsize=(10, 5.2), dpi=150)
other = [l not in top for l in loop["label"]]
ax.scatter([s for s, o in zip(secs, other) if o], [n for n, o in zip(num, other) if o], s=14, c="#b9c2c8",
           label=f"{loop['label'].n_unique() - len(top)} other names", zorder=2)
for i, name in enumerate(top):
    m = [l == name for l in loop["label"]]
    ax.scatter([s for s, k in zip(secs, m) if k], [n for n, k in zip(num, m) if k], s=18, zorder=3,
               color=plt.cm.tab10(i), label=f"{name} ({sum(m)})")
ax.set_xlabel("seconds after 20:09:40 UTC, 18 June 2026")
ax.set_ylabel("page number in LoopNextWord<number>")
ax.set_title(f"311 new pages in 39 seconds under {loop['label'].n_unique()} names, numbered by one counter (100000 + 20k, k = 130…300)", fontsize=10.5)
ax.legend(fontsize=8, frameon=False, loc="lower right")
for s in ("top", "right"): ax.spines[s].set_visible(False)
ax.text(0.01, 0.97, f"Spearman (time, page number) = {rank:.3f}\nall 314 pages of the burst deleted by the admin; none of the 311 written again",
        transform=ax.transAxes, va="top", fontsize=8.5, color="#444")
fig.tight_layout(); Path("report/figures").mkdir(parents=True, exist_ok=True)
fig.savefig("report/figures/broadcast.png"); print("report/figures/broadcast.png", loop["label"].n_unique(), "names on the 311", rank)
