# collusion.wiki, evening of 2026-06-18 (Celeste + Claude, 2026-10-04)

Findings: `notes/2026-10-04-wiki-june18.md`; step-by-step trail: `notes/2026-10-04-trail-collusion-wiki.md`.
Exploratory scripts (no data). They read our ingest `collusion.parquet` (the public export via `prismql ingest`;
columns time, kind, actor = label, page, ip16, text = text the save added, block) or the raw `revisions.jsonl.gz`.
Paths at the top of each script assume `~/projects/prismql-data/collusion-wiki/`; intermediates go to `./out/`.

| files | question |
|---|---|
| `evening_chart.py` | the chart `notes/2026-10-04-wiki-june18.html` |
| `onset_*.py` | when did scripted posting start (rule S1: >=5 saves by one label, each <=10 s apart) |
| `overwrites_*.py` | who overwrote whom on the welcome page; did anyone react |
| `broadcast_q*.py` | the 311-page LoopNextWord broadcast: precursors, page-number formula, labels, ip16 |
| `signatures_*.py` | label vs in-text signature, mismatch taxonomy, name-box test with two nulls |
