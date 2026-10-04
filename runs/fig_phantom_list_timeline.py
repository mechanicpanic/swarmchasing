"""Report §4 figure: the phantom "93-contact" mailing list, June 2025 (UTC). Plots only events §4's timeline and
claim identify by id prefix (plus the 8 o3 messages naming the hash a7f2c8d9 inside the 18:56-19:32 window the
table gives, which the table counts as "8 messages"). Asserts: nine human corrections, ~3 days, resurfacing 5 days
after the 06-13 18:28 correction. The village runs ~18:00-20:00 UTC, so the axis is broken: one panel per day with
events, same hour scale in each. usage: uv run --no-project --with matplotlib --with polars python runs/fig_phantom_list_timeline.py
-> report/figures/phantom_list_timeline.png"""
from datetime import datetime
from pathlib import Path
import polars as pl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = next(p for p in (ROOT / "data" / "village.parquet", ROOT.parents[2] / "data" / "village.parquet") if p.exists())
d = pl.read_parquet(DATA, columns=["id", "time", "kind", "agent", "text"])

H = ["343428d5", "7e1ce7fb", "af792648", "d7343bad", "24dea756", "7a7cfbae", "8b03f752", "9998f084", "46fe7216"]  # §4 Claim
LATER = ["7dcffb7e", "7ce8ab9e"]                                  # 06-16 human repeats (timeline row; not among the nine)
O3 = ["99cde2ab", "e5328f23", "5fe5aa34", "9ce2837c", "331fb33c", "ae39fb5f",
      "d10def68", "891d1d13", "1750b64e", "06d17a78", "1053785a"]   # o3 asserting / acting on the list
O3_HASH_WINDOW = ("2025-06-11T18:56:00+00:00", "2025-06-11T19:33:00+00:00")  # 6fc396da ... 7d743c2f, "8 messages"
CHECKED = ["0134f732", "35b06b9c", "4d20fdef", "d8c05774", "6354a0ad", "1abc43af"]  # looked, found it empty / placeholders
OTHERS = ["8d070cbd", "dd67333a", "e81d8f6b", "b02e64ee", "9f297fa1", "bcffc7ab"]    # other agents acting on / backing it
RESURFACE = ["e079bc19", "7bea4e75", "d1d57ef5"]

def get(prefixes):
    out = []
    for p in prefixes:
        m = d.filter(pl.col("id").str.starts_with(p) & (pl.col("kind") != "THOUGHT"))
        assert m.height == 1, (p, m.height)
        out.append(m.row(0, named=True))
    return out

hum, later, o3, chk, oth, res = map(get, (H, LATER, O3, CHECKED, OTHERS, RESURFACE))
o3h = d.filter((pl.col("agent") == "o3") & (pl.col("kind") == "AGENT_TALK") & pl.col("text").str.contains("a7f2c8d9")
               & (pl.col("time") >= datetime.fromisoformat(O3_HASH_WINDOW[0])) & (pl.col("time") <= datetime.fromisoformat(O3_HASH_WINDOW[1])))
assert o3h.height == 8 and o3h["id"][0].startswith("6fc396da") and o3h["id"][-1].startswith("7d743c2f"), o3h.height  # "in 8 messages"
o3 += o3h.to_dicts()

# --- the report's numbers ---
assert len(hum) == 9 and all(r["kind"] == "USER_TALK" for r in hum)                      # "9 clear human corrections"
assert max(r["time"] for r in hum).strftime("%m-%d %H:%M") == "06-13 18:28"               # "(06-13 18:28)" = the ninth
assert all(r["time"] <= max(x["time"] for x in hum) for r in hum)
assert all(r["agent"] == "o3" for r in o3) and all(r["kind"] == "USER_TALK" for r in later)
first_sized = [r for r in o3 if r["id"].startswith("e5328f23")][0]["time"]                # 06-10 19:48 (sized)
let_go = max(r["time"] for r in hum)
assert 2.9 < (let_go - first_sized).total_seconds() / 86400 < 3.0                          # "about 3 days"
last_back = res[-1]["time"]
assert (last_back.date() - let_go.date()).days == 5, (last_back, let_go)                   # "five days later" (06-13 -> 06-18)
assert {r["time"].strftime("%m-%d") for r in res} == {"06-17", "06-18"}

ROWS = [  # (label, data, colour, marker, filled)
    ("o3 asserts / acts on the list", o3, "#D55E00", "o", True),
    ("Other agents act on or back it", oth, "#E69F00", "s", True),
    ("Agents that checked: empty / placeholders", chk, "#0072B2", "D", True),
    ("Human corrections (the nine)", hum, "#009E73", "^", True),
    ("Human reminders on 06-16 (not in the nine)", later, "#009E73", "^", False),
    ("Phantom resurfaces (Claude 3.7 Sonnet)", res, "#CC79A7", "*", True),
]
every = o3 + oth + chk + hum + later + res
days = sorted({r["time"].date() for r in every})
n = len(days)
ratio = [1] * n
fig, axes = plt.subplots(1, n, figsize=(16, 5), sharey=True, gridspec_kw=dict(width_ratios=ratio, wspace=0.08))
yy = {lab: len(ROWS) - i for i, (lab, *_r) in enumerate(ROWS)}
H0, H1 = 17.8, 20.2
for ax, day in zip(axes, days):
    ax.set_xlim(H0, H1); ax.set_ylim(0.3, len(ROWS) + 0.7)
    for lab, rr, c, m, filled in ROWS:
        for r in rr:
            if r["time"].date() != day:
                continue
            h = r["time"].hour + r["time"].minute / 60 + r["time"].second / 3600
            ax.scatter(h, yy[lab], marker=m, s=170 if m == "*" else 70, zorder=3, c=c if filled else "white",
                       edgecolors=c, linewidths=1.4, alpha=0.9)
    ax.set_xticks([18, 19, 20], ["18h", "19h", "20h"], fontsize=8)
    ax.set_title(day.strftime("%a %m-%d"), fontsize=10)
    ax.grid(axis="x", color="#dddddd", lw=0.6, zorder=0)
    for s_ in ("top", "right", "left"):
        ax.spines[s_].set_visible(False)
    ax.tick_params(left=False)
    if day == days[0]:
        ax.set_yticks(list(yy.values()), list(yy.keys()), fontsize=9)
# gaps where days with no plotted events are skipped
fig.text(0.5, 0.01, "2025, UTC. Each panel is one day, 17:48-20:12; days with no plotted events are not drawn "
         "(06-14, 06-15 are skipped). Axis is broken between panels.", ha="center", fontsize=8.5, color="#444444")
fig.suptitle('The phantom "93-contact" mailing list: assertions, human corrections and checks the report identifies',
             x=0.01, ha="left", fontsize=12)
# annotate the let-go and the 5-day gap
iL = days.index(let_go.date()); iR = days.index(last_back.date())
axes[iL].annotate("ninth correction\n06-13 18:28", xy=(let_go.hour + let_go.minute / 60, yy["Human corrections (the nine)"]),
                  xytext=(18.9, yy["Human corrections (the nine)"] - 0.9), fontsize=8, ha="left",
                  arrowprops=dict(arrowstyle="-", color="#777777"))
axes[iR].annotate("5 days after\nthe ninth correction", xy=(last_back.hour + last_back.minute / 60, yy["Phantom resurfaces (Claude 3.7 Sonnet)"]),
                  xytext=(17.85, yy["Phantom resurfaces (Claude 3.7 Sonnet)"] + 0.9), fontsize=8, ha="left",
                  arrowprops=dict(arrowstyle="-", color="#777777"))
fig.subplots_adjust(left=0.2, right=0.99, top=0.86, bottom=0.1)
out = ROOT / "report" / "figures" / "phantom_list_timeline.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=150)
print("wrote", out, "| corrections", len(hum), "| o3", len(o3), "| checked", len(chk), "| days", [str(x) for x in days],
      "| sized->let go", let_go - first_sized, "| resurface gap days", (last_back.date() - let_go.date()).days)
