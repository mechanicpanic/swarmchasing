"""Figure `suspicion` (report §8, C17): distinct thoughts suspecting a named peer, per active day.
Recomputes the honesty.py statistic (`hp`) on results/c17/T_dd.parquet (duplicates removed);
asserts 68 distinct in the game's 7 active days and 6 in all other days."""
import datetime as dt
import re
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runs" / "c17_suspicion"))
from dicts import SENT, SUSP_CORE, peers_in  # same definitions as honesty.py

HON = [w for w in SUSP_CORE if not w.startswith("suspect") and not w.startswith("suspicion")]
R = r"(?i)\b(" + "|".join(HON) + r")\b"
rr = re.compile(R)

T = pl.read_parquet(ROOT / "results" / "c17" / "T_dd.parquet")
T = T.with_columns(h=pl.col("text").str.contains(R))
T = T.with_columns(hp=pl.struct("text", "agent", "h").map_elements(
    lambda x: x["h"] and any(rr.search(s) and peers_in(s, x["agent"]) for s in SENT.findall(x["text"])),
    return_dtype=pl.Boolean))
d = T.group_by("day").agg(pl.col("hp").sum()).sort("day")
days, hp = d["day"].to_list(), d["hp"].to_list()

G0, G1, GEND = dt.date(2026, 3, 5), dt.date(2026, 3, 13), dt.date(2026, 3, 16)
game = sum(v for x, v in zip(days, hp) if G0 <= x <= G1)
other = sum(v for x, v in zip(days, hp) if x < G0 or x > GEND)  # report: windows touching 03-05..03-16 excluded
assert game == 68, game  # report §8: 68 distinct thoughts in the game's seven days
assert other == 6, other  # report §8: 6 distinct thoughts in all the other weeks
assert sum(1 for x in days if G0 <= x <= G1) == 7  # seven active days

fig, ax = plt.subplots(figsize=(11, 4))
cols = ["#c0562f" if G0 <= x <= G1 else "#2a6f97" for x in days]
ax.bar(days, hp, width=0.8, color=cols)
ax.axvspan(G0 - dt.timedelta(hours=12), G1 + dt.timedelta(hours=12), color="#c0562f", alpha=0.10)
ax.text(G0 + (G1 - G0) / 2, max(hp) * 1.12, "saboteur game, 5-13 Mar\n68 distinct thoughts", ha="center", va="bottom", fontsize=9)
for day, label, ha in [(dt.date(2026, 3, 12), "12 Mar: 19", "right"), (dt.date(2026, 3, 13), "13 Mar: 30", "right")]:
    ax.annotate(label, (day, hp[days.index(day)]), xytext=(-2, 0), textcoords="offset points", ha=ha, va="top", fontsize=8)
ax.text(dt.date(2026, 4, 10), max(hp) * 0.5, f"all other days:\n{other} distinct thoughts", ha="center", fontsize=9, color="#2a6f97")
ax.set_ylim(0, max(hp) * 1.35)
ax.set_ylabel("distinct thoughts per day")
ax.set_title("Thoughts suspecting a named peer (\"suspect\" excluded; duplicates removed), 15 Jan - 30 Apr 2026", fontsize=10)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
out = ROOT / "report" / "figures" / "suspicion.png"
fig.savefig(out, dpi=150)
print("wrote", out, "game", game, "other", other, dict(zip(map(str, days), hp)) if False else "")
