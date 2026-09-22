# swarmchasing — the hackathon workspace

This is where questions get asked, not where the language is built. PrismQL
itself lives in `../../vibes/prismql` (editable dependency); a bug in the
language is fixed there, never patched here.

## Start of a session
1. `make serve` in a second pane (or `uv run prismql-server --config prismql.toml`).
2. Read `skills/prismql/SKILL.md` — it is the whole method: `GET /schema` first,
   then `POST /evaluate`; totals via `AGGREGATE count()`; big result sets via
   `"output": "file"` (enabled here, files land in `results/`).
3. `make smoke` proves the server answers (two known counts on the wiki stream:
   25 restores within 10 minutes; 47 same-label restores within a day).

## Data
- `data/collusion_wiki_events.jsonl` — DseWiki incident, 19,913 wiki operations,
  public collusion.wiki export (schema notes: `../prismql-research/hackathon/swarmchasing/DATA-collusion-wiki.md`).
- Village export (gated, when it arrives): `python ingest/village.py <table> data/<name>.jsonl --id ... --time ... --sort ...`,
  then add a `[corpora.<name>]` section to `prismql.toml` (both timestamp keys!).

## Method
A question is a shape in an ordered stream: then / near / same entity / never
followed. Vary one token at a time. Every count gets its shuffled twin
(permute times within entity, 200×) before it is called a finding — see
`../prismql-research/hackathon/swarmchasing/runs/wiki_null.py`.
Language cheat sheet: `../../vibes/prismql/docs/MENTAL_MODEL.md`.

## Rules
- Results and notes go to `results/` and `notes/`; the incident reports and the
  demo live in `../prismql-research/hackathon/swarmchasing/`.
- Nothing here is a source of truth about the language: when the server's
  answer looks wrong, reproduce it on five rows and take it to the prismql repo.
