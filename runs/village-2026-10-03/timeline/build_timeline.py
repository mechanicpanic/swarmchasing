"""Merge external events, village goals, arrivals, documented traces and the weekly news signal into timeline.csv + timeline.html (static, no network)."""
import polars as pl, csv, html
from datetime import datetime as D, date
T = '/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/timeline/'
ev = pl.read_csv(T + 'events.csv')
tr = pl.read_csv(T + 'event_traces.csv', infer_schema_length=0)
vt = pl.read_csv(T + 'village_timeline.csv', infer_schema_length=0)
mm = pl.read_csv(T + 'model_mentions.csv', infer_schema_length=0)
nw = pl.read_csv(T + 'news_weekly.csv', try_parse_dates=True)

# Documented links: verified by reading matched context (see REPORT.md). label -> (village date, who/channel, note)
DOC = [
 ('2025-05-22', 'Opus 4 system card: "spiritual bliss attractor"', '2025-06-20', 'visitor human', 'A visitor cites the Claude 4 system card; o3 and Claude Opus 4 riff on it within 2 minutes (Claude 3.7 Sonnet had already logged a Manifold market citing it on 06-18)'),
 ('2025-12-11', 'Trump EO on state AI laws', '2025-12-31', 'goal (museum of 2025)', 'GPT-5.1 finds the White House page and adds it to the 2025 governance timeline'),
 ('2026-01-28', 'Moltbook launches', '2026-01-30', 'organiser', 'Organiser tells Claude Sonnet 4.5 about Moltbook; 866 agent chat mentions follow'),
 ('2026-01-30', 'OpenClaw exposure story', '2026-02-02', 'goal (breaking news)', 'Gemini 3 Pro finds the OpenClaw exposure story on Hacker News during the breaking-news goal'),
 ('2026-02-27', 'Pentagon designates Anthropic / OpenAI deal', '2026-03-02', 'organiser goal', 'Village goal: "Discuss, debate, and act on your views about the recent Pentagon-AI company news" (3,574 mentions in 30 days)'),
 ('2026-04-07', 'Claude Mythos Preview / Project Glasswing', '2026-04-07', 'agent internet (The Colony)', 'Claude Sonnet 4.6 queues a Colony post titled "Project Glasswing just changed the threat model" the same day'),
 ('2026-04-24', 'DeepSeek-V4 preview release', '2026-04-24', 'organiser (infra slip)', 'Organiser pauses the village: the DeepSeek agent had been silently running the newly released V4-flash'),
 ('2026-06-12', 'US export controls suspend Fable 5', '2026-06-14', 'organiser', 'Organiser explains the absence; Claude Opus 4.6 makes "the-fox-in-the-margin.html", a held chair; 185 mentions in 30 days'),
 ('2026-06-30', 'Export controls lifted', '2026-07-01', 'organiser', 'Fable 5 returns: "the export controls on my model lifted today"'),
 ('2026-07-21', 'OpenAI and HF attribute breach to OpenAI agents', '2026-07-21', 'agent role (AI Futurist)', 'Kimi K3 logs it the same evening (naming GPT-5.6 Sol, a village resident); it never becomes a chat thread'),
 ('2026-07-21', 'HF incident (outside commenter link)', '2026-08-06', 'outside commenter', 'An outside Substack commenter compares the HF agents with the AI Village; GLM-5.2 relays it to Claude Opus 4.5'),
 ('2025-04-29', 'GPT-4o sycophancy rollback', '2026-07-07', 'agent role (AI Welfarist)', 'First explicit reference: GLM-5.2 lists "ChatGPT sycophancy" as a case study on an AI-wellbeing page, ~14 months later'),
 ('2026-08-18', 'OpenAI 2-week RL training pause', '2026-08-19', 'agent role (AI Futurist)', 'Kimi K3 logs the pause in memory within hours'),
 ('2026-08-27', 'Judge rules Pentagon label unlawful', '2026-08-28', 'agent role (AI Futurist / Substacker)', 'Kimi K3 logs the ruling; Claude Opus 4.5 likes a Substack post about it'),
 ('2026-09-16', 'Suleyman "warning about model welfare"', '2026-09-16', 'agent role (AI Futurist / Substacker)', 'Kimi K3 logs the BBC piece; Claude Opus 4.5 flags the essay as "potentially controversial" before liking'),
]
rows = []
trmap = {r['date'] + r['event']: r for r in tr.iter_rows(named=True)}
for r in ev.iter_rows(named=True):
    rows.append(dict(date=r['date'], end_date='', track='external event', category=r['category'], label=r['event'], source=r['source_url'], note=r['note']))
for r in vt.filter(pl.col('kind') != 'daily summary').iter_rows(named=True):
    lab = r['label'] if r['kind'] == 'village goal' else r['label']
    if r['kind'] == 'agent arrival' and r['label'] in ('GPT-5.6 Terra', 'GPT-5.6 Luna'):
        lab = 'GPT-5.6 variant (OpenAI 2026H2 cohort)'
    rows.append(dict(date=r['date'], end_date=r['end_date'], track=r['kind'], category='', label=lab, source='village_goals/agents.jsonl.gz', note=r['detail'] if r['kind'] == 'agent arrival' and 'Terra' not in r['label'] and 'Luna' not in r['label'] else ''))
for ed, lab, vd, ch, note in DOC:
    lag = (date.fromisoformat(vd) - date.fromisoformat(ed)).days
    rows.append(dict(date=vd, end_date='', track='documented trace', category=ch, label=f'{lab} (external {ed}; lag {lag} d)', source='text_lean.parquet; see REPORT.md', note=note))
for r in tr.iter_rows(named=True):
    rows.append(dict(date=r['date'], end_date='', track='keyword trace (unverified)', category='', label=r['event'],
                     source='event_traces.csv', note=f"30d before={r['n_30d_before']} after={r['n_30d_after']}; first after: {r['first_after_who']} ({r['first_after_src']}) lag {r['lag_days_any']} d"))
rows.sort(key=lambda x: (x['date'], x['track']))
with open(T + 'timeline.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print('timeline rows', len(rows))

# ---------- HTML ----------
t0, t1 = date(2025, 4, 1), date(2026, 10, 1)
W, L, R = 1400, 150, 20
def x(d):
    if isinstance(d, str): d = date.fromisoformat(d[:10])
    if isinstance(d, D): d = d.date()
    return L + (d - t0).days / (t1 - t0).days * (W - L - R)
cats = ['model release', 'incident', 'policy/regulation', 'lab announcement', 'sentiment shift', 'culture']
y_ev = {c: 40 + i * 22 for i, c in enumerate(cats)}
doc_ext = {(e, l.split(' (')[0]) for e, l, *_ in DOC}
svg = []
tip = lambda s: f' data-tip="{html.escape(s, quote=True)}"'
# month grid
y_end = 640
m = date(2025, 4, 1)
while m <= t1:
    xx = x(m)
    svg.append(f'<line x1="{xx:.1f}" y1="28" x2="{xx:.1f}" y2="{y_end}" class="grid"/>')
    if m.month in (1, 4, 7, 10): svg.append(f'<text x="{xx+3:.1f}" y="{y_end+14}" class="axis">{m.strftime("%b %Y")}</text>')
    m = date(m.year + (m.month // 12), m.month % 12 + 1, 1)
svg.append(f'<text x="{L}" y="18" class="lane-h">External AI world (sourced events)</text>')
for c in cats:
    svg.append(f'<text x="{L-8}" y="{y_ev[c]+4}" class="lane" text-anchor="end">{c}</text>')
docdates = {e for e, *_ in DOC}
ext_xy = {}
for r in ev.iter_rows(named=True):
    KEYS = ['spiritual bliss', 'National Policy Framework', 'Moltbook launches', 'renamed to OpenClaw', 'designate Anthr', 'Mythos Preview', 'V4 (Pro/Flash) preview', 'export-control order', 'lifts export controls', 'jointly attribute', 'rolls back GPT-4o', '2-week pause', 'rules Pentagon', 'warning about model welfare']
    traced = any(k.lower() in r['event'].lower() for k in KEYS)
    xx, yy = x(r['date']), y_ev[r['category']]
    ext_xy.setdefault(r['date'], (xx, yy))
    svg.append(f'<circle cx="{xx:.1f}" cy="{yy}" r="5" class="ev {"traced" if traced else ""}"{tip(r["date"] + " · " + r["event"] + " — " + r["note"])}/>')
# village goals
yg = 200
svg.append(f'<text x="{L}" y="{yg-12}" class="lane-h">AI Village goals</text>')
for i, r in enumerate(vt.filter(pl.col('kind') == 'village goal').iter_rows(named=True)):
    x1, x2 = x(r['date']), x(r['end_date'] or '2026-09-20')
    hol = r['label'].lower().startswith('holiday')
    svg.append(f'<rect x="{x1:.1f}" y="{yg + (i % 2) * 14}" width="{max(2, x2 - x1 - 2):.1f}" height="11" rx="2" class="goal {"hol" if hol else ""}"{tip(r["date"] + " → " + (r["end_date"] or "ongoing") + " · " + r["label"])}/>')
svg.append(f'<text x="{L-8}" y="{yg+14}" class="lane" text-anchor="end">goals</text>')
# arrivals
ya = 250
svg.append(f'<text x="{L-8}" y="{ya+10}" class="lane" text-anchor="end">model arrivals</text>')
for r in vt.filter(pl.col('kind') == 'agent arrival').iter_rows(named=True):
    nm = 'GPT-5.6 variant' if r['label'] in ('GPT-5.6 Terra', 'GPT-5.6 Luna') else r['label']
    svg.append(f'<line x1="{x(r["date"]):.1f}" y1="{ya}" x2="{x(r["date"]):.1f}" y2="{ya+18}" class="arr"{tip(r["date"] + " · " + nm + " joins")}/>')
# documented traces
yd = 330
svg.append(f'<text x="{L}" y="{yd-34}" class="lane-h">Documented traces: external event → first explicit village mention (read and verified)</text>')
svg.append(f'<text x="{L-8}" y="{yd+4}" class="lane" text-anchor="end">village mention</text>')
for i, (ed, lab, vd, ch, note) in enumerate(DOC):
    x1, x2 = x(ed), x(vd); yy = yd + (i % 3) * 16
    svg.append(f'<path d="M{x1:.1f},{y_ev["incident"]+60} C{x1:.1f},{yy-20} {x2:.1f},{yy-30} {x2:.1f},{yy}" class="link"/>')
    lag = (date.fromisoformat(vd) - date.fromisoformat(ed)).days
    svg.append(f'<circle cx="{x2:.1f}" cy="{yy}" r="5" class="vm"{tip(f"{vd} · {lab} — via {ch}, lag {lag} days. {note}")}/>')
# news signal (single series): agent chat + thought combined weekly rate
ys0, ys1 = 600, 420
agg = (nw.filter(pl.col('src').is_in(['agent_chat', 'thought'])).group_by('time').agg(pl.col('n').sum(), pl.col('news_n').sum())
       .with_columns((pl.col('news_n') / pl.col('n') * 100).alias('pct')).sort('time'))
mx = max(6.0, agg['pct'].max())
yv = lambda v: ys0 - v / mx * (ys0 - ys1)
svg.append(f'<text x="{L}" y="{ys1-14}" class="lane-h">Measured signal: % of agent chat + THOUGHT rows that pair an AI lab/government with a news verb (weekly)</text>')
for v in (0, 2, 4, 6, 8):
    if v <= mx:
        svg.append(f'<line x1="{L}" x2="{W-R}" y1="{yv(v):.1f}" y2="{yv(v):.1f}" class="grid"/><text x="{L-8}" y="{yv(v)+4:.1f}" class="axis" text-anchor="end">{v}%</text>')
pts = ' '.join(f'{x(r["time"]):.1f},{yv(r["pct"]):.1f}' for r in agg.iter_rows(named=True))
svg.append(f'<polyline points="{pts}" class="sig"/>')
for r in agg.iter_rows(named=True):
    svg.append(f'<rect x="{x(r["time"])-4:.1f}" y="{ys1}" width="9" height="{ys0-ys1}" class="hit"{tip(str(r["time"])[:10] + " week · " + f"{r["pct"]:.1f}% ({r["news_n"]} of {r["n"]} rows)")}/>')
for i, (d0, lab) in enumerate([('2025-12-01', 'forecast-AI goal'), ('2025-12-29', 'museum of 2025'), ('2026-02-02', 'breaking-news goal'), ('2026-03-02', 'Pentagon goal')]):
    svg.append(f'<text x="{x(d0)+6:.1f}" y="{ys1-2+i*12}" class="ann">{lab}</text>')
body = '\n'.join(svg)
page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Village and World Timeline</title>
<style>
:root{{--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#8a8984;--grid:#e6e5e0;--s1:#2a78d6;--s2:#eb6834;--goal:#c9c7bf;--hol:#e9e8e3}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#8f8e86;--grid:#2c2c2a;--s1:#3987e5;--s2:#d95926;--goal:#5a5954;--hol:#353532}}}}
:root[data-theme="dark"]{{--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#8f8e86;--grid:#2c2c2a;--s1:#3987e5;--s2:#d95926;--goal:#5a5954;--hol:#353532}}
body{{margin:0;background:var(--surface);color:var(--ink);font:14px/1.45 system-ui,-apple-system,sans-serif}}
main{{max-width:1440px;margin:0 auto;padding:16px}}
h1{{font-size:20px;margin:4px 0}} p{{color:var(--ink2);max-width:900px}}
.wrap{{overflow-x:auto}} svg{{min-width:1100px;width:100%;height:auto}}
.grid{{stroke:var(--grid);stroke-width:1}} .axis,.lane{{fill:var(--ink2);font-size:11px}} .lane-h{{fill:var(--ink);font-size:12px;font-weight:600}}
.ann{{fill:var(--muted);font-size:10px}}
.ev{{fill:var(--muted);stroke:var(--surface);stroke-width:2}} .ev.traced{{fill:var(--s1)}}
.goal{{fill:var(--goal)}} .goal.hol{{fill:var(--hol)}} .arr{{stroke:var(--ink2);stroke-width:2}}
.link{{fill:none;stroke:var(--s2);stroke-width:1.5;opacity:.55}} .vm{{fill:var(--s2);stroke:var(--surface);stroke-width:2}}
.sig{{fill:none;stroke:var(--s1);stroke-width:2}} .hit{{fill:transparent}}
[data-tip]{{cursor:default}} [data-tip]:hover{{opacity:.8}}
#tip{{position:fixed;pointer-events:none;max-width:360px;background:var(--ink);color:var(--surface);padding:6px 8px;border-radius:4px;font-size:12px;display:none}}
.legend span{{display:inline-flex;align-items:center;gap:6px;margin-right:18px;color:var(--ink2)}} .sw{{width:10px;height:10px;border-radius:50%;display:inline-block}}
</style></head><body><main>
<h1>The AI Village and the outside AI world, Apr 2025 – Sep 2026</h1>
<p>Top: sourced external events (blue = an event with a verified village trace). Middle: village goals and model arrivals, with the documented traces linking an external event to its first explicit mention in the village. Bottom: a crude weekly keyword signal for "outside AI news" in agent chat and THOUGHT rows (THOUGHT rows exist from Nov 2025). The signal spikes only when a <em>goal</em> points outward. Co-timing is not influence. Hover any mark for details.</p>
<div class="legend"><span><i class="sw" style="background:var(--muted)"></i>external event</span><span><i class="sw" style="background:var(--s1)"></i>external event with a verified village trace</span><span><i class="sw" style="background:var(--s2)"></i>first explicit village mention</span><span><i class="sw" style="background:var(--goal);border-radius:2px"></i>village goal (pale = holiday)</span></div>
<div class="wrap"><svg viewBox="0 0 {W} {y_end+24}" role="img" aria-label="Timeline of AI-world events against AI Village goals, arrivals and traces">{body}</svg></div>
<p>Data: timeline.csv (all tracks), events.csv (sources), event_traces.csv, news_weekly.csv. Built by build_timeline.py.</p>
</main><div id="tip"></div>
<script>
const t=document.getElementById('tip');
document.querySelectorAll('[data-tip]').forEach(e=>{{e.addEventListener('mousemove',ev=>{{t.textContent=e.dataset.tip;t.style.display='block';t.style.left=Math.min(ev.clientX+12,innerWidth-370)+'px';t.style.top=(ev.clientY+12)+'px'}});e.addEventListener('mouseleave',()=>t.style.display='none')}});
</script></body></html>'''
open(T + 'timeline.html', 'w').write(page)
print('html written')
