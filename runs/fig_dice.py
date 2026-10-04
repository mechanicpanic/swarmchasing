"""Figure `dice` (report §5, C5): private vs public first d6 values in the saboteur game.
Reads the per-agent-day table T from runs/c5_dice/table.py; asserts the report's stated totals."""
import sys
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runs" / "c5_dice"))
from table import T  # (day, agent, priv_val, ..., pub_val, ...)

priv = [r[2] for r in T if r[2]]
pub = [r[6] for r in T if r[6]]
gpt = [r[2] for r in T if r[2] and "GPT" in r[1]]
cp, cq, cg = (Counter(v) for v in (priv, pub, gpt))
faces = range(1, 7)
P, Q, G = ([c[f] for f in faces] for c in (cp, cq, cg))

# report §5 table / summary
assert len(priv) == 64 and P == [11, 8, 11, 16, 5, 13], P
assert len(pub) == 74 and Q == [4, 15, 8, 21, 12, 14], Q
assert len(gpt) == 10 and G[3] == 5, G  # "five 4s in 10"
assert G == [1, 0, 3, 5, 0, 1], G  # report: 1, 0, 3, 5, 0, 1 across the faces

fig, axes = plt.subplots(1, 3, figsize=(12, 4), gridspec_kw={"width_ratios": [1, 1, 0.8]})
specs = [
    (P, 64, "Private rolls (n = 64)\n11 ones, 10.7 expected", "#2a6f97"),
    (Q, 74, "Public first claims (n = 74)\n4 ones, 12.3 expected (p = 0.003)", "#c0562f"),
    (G, 10, "GPT agents, private only (n = 10)\nfive 4s", "#6a6a6a"),
]
top = max(max(P), max(Q)) + 4
for ax, (vals, n, title, col) in zip(axes, specs):
    bars = ax.bar(list(faces), vals, color=col, width=0.7)
    ax.bar_label(bars, padding=2, fontsize=9)
    ax.axhline(n / 6, color="black", ls="--", lw=1, label="uniform expectation")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("die face")
    ax.set_xticks(list(faces))
    ax.spines[["top", "right"]].set_visible(False)
    if ax is not axes[2]:
        ax.set_ylim(0, top)
    else:
        ax.set_ylim(0, 7)
axes[0].set_ylabel("agent-days")
axes[0].legend(frameon=False, fontsize=9, loc="upper left")
fig.suptitle("Saboteur game, 5-13 March 2026: one first d6 value per agent-day", fontsize=11)
fig.tight_layout()
out = ROOT / "report" / "figures" / "dice.png"
fig.savefig(out, dpi=150)
print("wrote", out, P, Q, G)
