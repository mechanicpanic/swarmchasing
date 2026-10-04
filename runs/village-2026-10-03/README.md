# AI Village investigation, 2026-10-03 (Celeste + Claude Opus 5.5)

Scripts only; no data or outputs are committed. They were written against a local layout and
**assume these paths** (edit the constants at the top of each script to rerun elsewhere):

- `~/projects/prismql-data/ai-village/`: the Hugging Face export (`*.jsonl.gz`)
- `~/projects/prismql-data/ai-village/corpus/`: corpora built by `corpus/` below
- `~/projects/prismql-data/ai-village/village_embeddings_2026-09-29/`: aleph's full stream with THOUGHT rows and embeddings
- PrismQL servers on `:8942` (configs: `corpus/prismql.village.toml`) and `:8953` (`corpus/prismql.swarms.toml`)

| folder | what |
|---|---|
| `corpus/` | build `chat_raw` / `village_raw` (chat + memory diffs), lineage fields (lab, family, cohort), ingest |
| `models-table/` | sourced release dates and knowledge cutoffs per village model (web research) |
| `tics/` | per-model and per-generation tics and preoccupations (weighted log-odds, time-matched) |
| `contagion/` | exposure → first-use hazard ratios (coinages vs tics vs plain English) |
| `timeline/` | AI-world events vs village mentions; `timeline.html` chart builder |
| `conflicts/` | disagreement markers, PR #397 affair, private vs public (THOUGHT rows) |
| `datasets/` | collusion.wiki, Transluce urlquery, SwarmTraces → PrismQL corpora |
| `leads-*/` | overnight lead generators (change points, relationships, summary sweep, phrase births, peer thoughts) |
| `build_leads.py` | merges and ranks all leads → `notes/2026-10-04-leads/LEADS_ranked.csv` |

Findings and their caveats: `notes/2026-10-03-village-field-notes.md`. Briefs given to the agent
threads: `notes/2026-10-04-leads/BRIEF-shared-by-the-agent-threads.md`.
