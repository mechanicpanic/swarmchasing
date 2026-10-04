"""Figure: the DSEwiki swarm's shape over time (saves per hour by label, admin deletes per hour).
Source of the numbers asserted below: notes/2026-10-03-dsewiki-report.md (branch docs/dsewiki-report).
uv run --with matplotlib --with polars python runs/fig_wiki_activity.py   -> report/figures/wiki_activity.png"""
import datetime as dt
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
d = pl.read_parquet(data_path("wiki_msgs.parquet"))

# A save = one revision (distinct rev of kind add/remove), admin ([Admin1]) excluded, as in the notes.
saves = (d.filter(pl.col("kind").is_in(["add", "remove"]) & (pl.col("label") != "[Admin1]"))
          .group_by("rev").agg(pl.col("time").min(), pl.col("label").first())
          .with_columns(hour=pl.col("time").dt.truncate("1h")))
dels = d.filter(pl.col("kind") == "delete").with_columns(hour=pl.col("time").dt.truncate("1h"))

# ---- checks against the notes (section 11 and Corpus line) ----
assert d.height == 26_655, d.height                                    # "wiki_msgs (26,655 rows"
daily = {k: v for k, v in saves.group_by(pl.col("time").dt.date().alias("day")).len().iter_rows()}
for day, n in {(6, 16): 2584, (6, 17): 1280, (6, 18): 6500, (6, 19): 504, (6, 20): 654,
               (6, 21): 655, (6, 22): 1061, (7, 1): 7, (7, 2): 14}.items():
    assert daily[dt.date(2026, *day)] == n, (day, daily[dt.date(2026, *day)], n)   # "Daily saves ... Jun 16 2,584 ..."
h8 = d.filter(pl.col("kind").is_in(["add", "remove"]) & (pl.col("time").dt.truncate("1h") == dt.datetime(2026, 6, 22, 8, tzinfo=dt.timezone.utc))).height
assert h8 == 725, h8                                                   # "725 rows in hour 08 of June 22" (add+remove rows, not saves)
last = saves.filter(pl.col("time").dt.date() == dt.date(2026, 6, 22))["time"].max()
assert last.strftime("%H:%M:%S") == "09:20:04", last                   # "last save 09:20:04"
assert dels.height == 5217, dels.height                                # "5,217 deletions"

# ---- plot ----
TOP = 8
saves = saves.with_columns(pl.col("label").replace("", "(blank name)"))
top = saves.group_by("label").len().sort("len", descending=True).head(TOP)
share_top = top["len"].sum() / saves.height          # computed here, not a number from the notes
top = top["label"].to_list()
saves = saves.with_columns(grp=pl.when(pl.col("label").is_in(top)).then(pl.col("label")).otherwise(pl.lit("other")))
t0, t1 = saves["hour"].min(), saves["hour"].max() + dt.timedelta(hours=1)
hours = pl.datetime_range(t0, t1, "1h", time_zone="UTC", eager=True)
wide = (saves.group_by("hour", "grp").len().pivot(on="grp", index="hour", values="len")
             .join(hours.to_frame("hour"), on="hour", how="right").sort("hour").fill_null(0))
order = ["other"] + top
colors = ["#bdbdbd", "#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9", "#7a5195", "#8c6d31"]
x = wide["hour"].to_list()
ys = [wide[c].to_list() for c in order]
dh = dels.group_by("hour").len().sort("hour")
UTC = dt.timezone.utc
zoom = (dt.datetime(2026, 6, 16, tzinfo=UTC), dt.datetime(2026, 6, 23, 12, tzinfo=UTC))
fig, axs = plt.subplots(3, 1, figsize=(10, 8.5), gridspec_kw={"height_ratios": [2.2, 2.2, 1.2]})
ax, axz, ax2 = axs
for a_, xlim in ((ax, None), (axz, zoom)):
    a_.stackplot(x, ys, labels=order, colors=colors, linewidth=0, step="mid")
    a_.set_ylabel("Saves per hour")
    if xlim: a_.set_xlim(*xlim)
ax.set_title(f"Wiki saves per hour, whole span (UTC). The 8 busiest writer names make up {share_top:.0%} of saves", loc="left", fontsize=10.5)
axz.set_title("Same data, June 16 to June 23", loc="left", fontsize=10.5)
axz.legend(loc="upper right", fontsize=8, ncol=1, frameon=False, title="writer name", title_fontsize=8.5)
ax.axvspan(*zoom, color="#000000", alpha=0.06, linewidth=0)
ax2.bar(dh["hour"].to_list(), dh["len"].to_list(), width=dt.timedelta(hours=1.5), color="#222222", linewidth=0)
ax2.set_ylabel("Admin deletes\nper hour")
ax2.set_title("Admin deletions per hour, whole span (UTC)", loc="left", fontsize=10.5)
span = (min(t0, dels["hour"].min()), max(t1, dels["hour"].max() + dt.timedelta(hours=1)))
ax.set_xlim(*span); ax2.set_xlim(*span)
ax2.set_xlabel("Date (UTC), 2026")
for a_ in (ax, ax2):
    a_.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0))
    a_.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
axz.xaxis.set_major_locator(mdates.DayLocator())
axz.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
axz.set_xlabel("Date (UTC), 2026")
for a_ in axs:
    a_.spines[["top", "right"]].set_visible(False); a_.tick_params(labelsize=8)
fig.tight_layout()
out = ROOT / "report" / "figures" / "wiki_activity.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=150)
print("wrote", out, "| top labels:", top, f"| top-8 share {share_top:.3f}")
