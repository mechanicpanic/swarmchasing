"""The evening of 2026-06-18 on collusion.wiki as one self-contained SVG/HTML timeline.

Per minute: saves by script-like labels vs the rest, the admin's deletions, the
314-page broadcast, and saves on the welcome page. A label counts as script-like
that evening when it made >=10 saves with at most 4 distinct texts or a median gap <=6 s.
"""

import sys
from pathlib import Path

import polars as pl

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else
           "~/projects/prismql-data/collusion-wiki/collusion.parquet").expanduser()
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "june18_evening.html")
T0, T1 = pl.datetime(2026, 6, 18, 17, 30, time_zone="UTC"), pl.datetime(2026, 6, 18, 22, 0, time_zone="UTC")
BROADCAST = r"(?i)loop\W+predicted\W+child\W+raw\W+investor"

df = pl.read_parquet(SRC, columns=["time", "actor", "page", "kind", "text"]).filter(pl.col("time").is_between(T0, T1))
saves = df.filter(pl.col("kind") == "save")
per = saves.sort("time").group_by("actor").agg(
    pl.len().alias("n"), pl.col("text").n_unique().alias("texts"),
    pl.col("time").diff().dt.total_seconds().median().alias("gap"))
scripty = per.filter((pl.col("n") >= 10) & ((pl.col("texts") <= 4) | (pl.col("gap") <= 6)))["actor"].to_list()
m = (df.with_columns(pl.col("time").dt.truncate("1m").alias("t"),
                     pl.col("actor").is_in(scripty).alias("script"),
                     pl.col("text").str.contains(BROADCAST).fill_null(False).alias("bc"),
                     (pl.col("page") == "WillkommenImWiki").alias("welcome"))
       .group_by("t").agg(
           ((pl.col("kind") == "save") & pl.col("script") & ~pl.col("bc")).sum().alias("script"),
           ((pl.col("kind") == "save") & ~pl.col("script") & ~pl.col("bc")).sum().alias("other"),
           ((pl.col("kind") == "save") & pl.col("bc")).sum().alias("bc"),
           (pl.col("kind") == "delete").sum().alias("deletes"),
           ((pl.col("kind") == "save") & pl.col("welcome")).sum().alias("welcome"))
       .sort("t"))

W, H, L, TOP = 1100, 360, 50, 20
mins = int((m["t"].max() - m["t"].min()).total_seconds() // 60) + 1
start = m["t"].min()
bw = (W - L - 10) / mins
ymax = max(1, int((m["script"] + m["other"] + m["bc"]).max()))
y = lambda v: TOP + (H - TOP - 40) * (1 - v / ymax)
parts = []
for r in m.iter_rows(named=True):
    i = int((r["t"] - start).total_seconds() // 60)
    x = L + i * bw
    base = 0
    for k, col in (("script", "var(--script)"), ("other", "var(--other)"), ("bc", "var(--bc)")):
        if r[k]:
            parts.append(f'<rect x="{x:.1f}" y="{y(base + r[k]):.1f}" width="{max(bw - .3, .8):.1f}" height="{y(base) - y(base + r[k]):.1f}" fill="{col}"><title>{r["t"]:%H:%M} {k}: {r[k]}</title></rect>')
            base += r[k]
    if r["deletes"]:
        parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{TOP}" y2="{H - 40}" stroke="var(--del)" stroke-width="2"><title>{r["t"]:%H:%M} admin deletions: {r["deletes"]}</title></line>')
    if r["welcome"]:
        parts.append(f'<rect x="{x:.1f}" y="{H - 30}" width="{max(bw - .3, .8):.1f}" height="12" fill="var(--welcome)" opacity="{min(1, .15 + r["welcome"] / 40):.2f}"><title>{r["t"]:%H:%M} welcome-page saves: {r["welcome"]}</title></rect>')
for h in range(18, 22):
    for mm in (0, 30):
        i = (h * 60 + mm) - (start.hour * 60 + start.minute)
        if 0 <= i < mins:
            x = L + i * bw
            parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{H - 40}" y2="{H - 34}" stroke="var(--fg)"/><text x="{x:.1f}" y="{H - 2}" font-size="11" text-anchor="middle" fill="var(--fg)">{h}:{mm:02d}</text>')
for v in (0, ymax // 2, ymax):
    parts.append(f'<text x="{L - 6}" y="{y(v) + 4:.1f}" font-size="11" text-anchor="end" fill="var(--fg)">{v}</text>')
parts.append(f'<text x="{L - 6}" y="{H - 21}" font-size="10" text-anchor="end" fill="var(--fg)">welcome</text>')

html = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>June 18 Evening</title><style>
:root{{--bg:#fbfaf7;--fg:#2b2b2b;--muted:#6b6b6b;--script:#c2410c;--other:#94a3b8;--bc:#7c3aed;--del:#dc2626;--welcome:#0f766e}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#16161a;--fg:#e7e5e4;--muted:#a8a29e;--other:#64748b}}}}
:root[data-theme="dark"]{{--bg:#16161a;--fg:#e7e5e4;--muted:#a8a29e;--other:#64748b}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0;padding:24px 16px;max-width:1140px;margin:auto}}
svg{{width:100%;height:auto}} .k span{{display:inline-block;width:12px;height:12px;margin:0 4px 0 14px;vertical-align:-1px}}
p{{color:var(--muted);max-width:75ch}}</style></head><body>
<h1>collusion.wiki, the evening of 18 June 2026 (UTC)</h1>
<p>Saves per minute. One admin cleanup (red) and no deletions after it; saves keep rising; the 314-page broadcast lands in 40 seconds (purple);
script-like labels (orange) take over, ending in a front-page overwrite war (teal strip = saves on the welcome page) that stops at 21:26:36.
Script-like = a label with ≥10 saves that evening and ≤4 distinct texts or a median gap ≤6 s ({len(scripty)} labels).</p>
<div class="k"><span style="background:var(--script)"></span>script-like labels<span style="background:var(--other)"></span>other labels<span style="background:var(--bc)"></span>314-page broadcast<span style="background:var(--del)"></span>admin deletions<span style="background:var(--welcome)"></span>welcome-page saves</div>
<svg viewBox="0 0 {W} {H}" role="img" aria-label="saves per minute">{''.join(parts)}</svg>
<p>Built by <code>runs/wiki-june18/evening_chart.py</code> from the public collusion.wiki export.</p></body></html>"""
OUT.write_text(html)
print(f"wrote {OUT}: {mins} minutes, {len(scripty)} script-like labels, max {ymax}/min")
