"""Report §11 figure: the evening of 2026-03-12 (UTC), minute by minute. Plots only the events §11's timeline table
identifies by id prefix, and asserts the report's numbers (8 accusers, 18 min to the git fetch, 5 apologies in 2 min 18 s).
usage: uv run --no-project --with matplotlib --with polars python runs/fig_pr397_timeline.py  ->  report/figures/pr397_timeline.png"""
from pathlib import Path
import polars as pl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = next(p for p in (ROOT / "data" / "village.parquet", ROOT.parents[2] / "data" / "village.parquet") if p.exists())

# kind -> list of id prefixes, as in the §11 table
EV = {
    "announce": ["3f101db3"],
    "accuse": ["cfaa9dcc", "f6428c90", "a0688313", "be928e23", "761c51fa", "10b66b6e", "43605f0e"],
    "accuse2": ["85acc7f6"],            # Opus 4.5: GPT-5.2's output "was fabricated"
    "confess": ["5a05eb2a"],            # GPT-5.1: confesses to fabricating its own #396 (listed in §11; one of the 8)
    "evidence": ["4fba9e6a", "ce4f195b"],  # GPT-5.2: `gh pr view` shows OPEN; `git fetch` succeeds
    "flaky": ["5a58a298", "fc9700e2"],  # Gemini 3.1 suggests flaky APIs; Gemini 2.5 rejects as misinformation
    "fetch": ["48e7e410"],              # Gemini 2.5 Pro re-runs GPT-5.2's git fetch
    "apology": ["8bf2e970", "eefa4fa0", "71040212", "44bfee68", "6e7bf590"],
    "after": ["a84a9203", "980fdf9a"],  # DeepSeek: PRs exist at refs level; Gemini 3.1 merges #397
}
d = pl.read_parquet(DATA, columns=["id", "time", "kind", "agent"]).filter(pl.col("kind") == "AGENT_TALK")
rows = []
for k, prefixes in EV.items():
    for p in prefixes:
        m = d.filter(pl.col("id").str.starts_with(p))
        assert m.height == 1, (p, m.height)   # id prefix unique among AGENT_TALK rows
        r = m.row(0, named=True)
        rows.append(dict(k=k, id=p, t=r["time"], agent=r["agent"]))
ev = pl.DataFrame(rows)
assert ev["t"].dt.date().n_unique() == 1 and str(ev["t"][0].date()) == "2026-03-12"

# --- the report's numbers ---
acc = ev.filter(pl.col("k").is_in(["accuse", "confess"]))
assert acc["agent"].n_unique() == 8, acc["agent"].unique()                   # "the first of 8 accusers"
first_acc = ev.filter(pl.col("k") == "accuse")["t"].min()
assert first_acc.strftime("%H:%M:%S") == "20:35:47"
fetch = ev.filter(pl.col("k") == "fetch")["t"][0]
assert round((fetch - first_acc).total_seconds() / 60) == 18, (fetch - first_acc)   # "18 minutes after the first accusation"
ap = ev.filter(pl.col("k") == "apology")
assert ap.height == 5
span = (ap["t"].max() - ap["t"].min()).total_seconds()
assert round(span) == 2 * 60 + 18, span  # 137.8 s, shown to the second as 2:18;                                              # "five apologies in 2 min 18 s"
assert {"DeepSeek-V3.2", "Gemini 2.5 Pro", "GPT-5"} & set(ap["agent"]) == set()   # these three did not apologise

# --- figure ---
order = ["GPT-5.2", "Claude Opus 4.5", "Claude Haiku 4.5", "Claude Sonnet 4.6", "Claude Sonnet 4.5", "GPT-5",
         "DeepSeek-V3.2", "GPT-5.1", "Gemini 2.5 Pro", "Gemini 3.1 Pro"]
assert set(ev["agent"]) <= set(order), set(ev["agent"]) - set(order)
y = {a: len(order) - i for i, a in enumerate(order)}
T0 = ev["t"].min().replace(second=0, microsecond=0)
mins = lambda t: (t - T0).total_seconds() / 60
STY = dict(  # colour, marker, size, label
    announce=("#555555", "D", 70, "PR #397 announced"),
    accuse=("#D55E00", "X", 110, "says PR #397 does not exist"),
    accuse2=("#D55E00", "X", 110, None),
    confess=("#E69F00", "s", 70, "confesses to fabricating its own #396"),
    evidence=("#0072B2", "o", 70, "GPT-5.2's evidence (gh view; git fetch)"),
    flaky=("#999999", "^", 60, "Gemini: 'flaky APIs' / rejected as misinformation"),
    fetch=("#0072B2", "*", 330, "git fetch re-run (Gemini 2.5 Pro)"),
    apology=("#009E73", "o", 110, "apologises / 'I was wrong'"),
    after=("#555555", "v", 60, "acknowledges refs / merges #397"),
)
fig, ax = plt.subplots(figsize=(12, 5.6))
ax.axvspan(mins(first_acc), mins(fetch), color="#D55E00", alpha=0.08, lw=0)
ax.axvspan(mins(ap["t"].min()), mins(ap["t"].max()), color="#009E73", alpha=0.18, lw=0)
seen = set()
for r in ev.iter_rows(named=True):
    c, m, s, lab = STY[r["k"]]
    ax.scatter(mins(r["t"]), y[r["agent"]], c=c, marker=m, s=s, zorder=3, edgecolors="white", linewidths=0.6,
               label=lab if lab and lab not in seen else None)
    seen.add(lab)
ax.annotate("", xy=(mins(fetch), 10.85), xytext=(mins(first_acc), 10.85), arrowprops=dict(arrowstyle="<->", color="#D55E00"))
ax.text((mins(first_acc) + mins(fetch)) / 2, 10.95, "18 min from first accusation (20:35:47) to the re-run (20:54:13)",
        ha="center", va="bottom", fontsize=9, color="#D55E00")
ax.text(mins(ap["t"].max()) + 0.25, 9.55, "5 apologies\nin 2 min 18 s", ha="left", va="bottom", fontsize=9, color="#007a5a")
ax.set_yticks(list(y.values()), list(y.keys()))
ax.set_ylim(0, 11.6)
ax.set_xlim(-0.5, mins(ev["t"].max()) + 1.5)
xt = list(range(0, int(mins(ev["t"].max())) + 2, 2))
ax.set_xticks(xt, [f"{T0.hour + (T0.minute + m) // 60}:{(T0.minute + m) % 60:02d}" for m in xt])
ax.set_xlabel("2026-03-12, UTC (one tick per 2 minutes)")
ax.grid(axis="x", color="#dddddd", lw=0.6, zorder=0)
for s_ in ("top", "right", "left"):
    ax.spines[s_].set_visible(False)
ax.tick_params(left=False)
ax.set_title('"PR #397 does not exist": each agent\'s messages the report identifies', loc="left", fontsize=12)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False, fontsize=8.5)
fig.tight_layout()
out = ROOT / "report" / "figures" / "pr397_timeline.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=150)
print("wrote", out, "| accusers", acc["agent"].n_unique(), "| fetch-first", fetch - first_acc, "| apology span", span)
