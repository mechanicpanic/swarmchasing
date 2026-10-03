# Review + Trails: the human side of the workflow

A small local app beside the PrismQL board, for the two things the board doesn't record:

- **Review** (`/`): a queue of result groups (from any PrismQL query) or of claims (any `leads.jsonl`).
  A human marks each ✔ true / ✘ false / ? unsure with a note; the export gives a precision per
  query. Claims show the claim, the dataset summary it disputes (when linked, e.g.
  `notes/2026-10-04-leads/summary_links.jsonl`), and the raw messages around the quoted one.
- **Trails** (`/trails`): an investigation as a tree. Each step = a question in plain words,
  what it follows up on, the query (or a note for work done elsewhere), its result size,
  review verdicts, and the conclusion. `trails.jsonl` holds the example trail
  "live and verified: village meme or trained tic?".

Run (needs the PrismQL venv for fastapi/uvicorn/polars):

    uv run --project <prismql checkout> python review_server.py --port 8960

Edit `SERVERS` at the top of `review_server.py` to point at your PrismQL servers and their
`prismql.toml` (the claims mode reads corpus Parquet paths from it). Verdicts go to
`verdicts.jsonl`, queues to `queues/`, trail steps to `trails.jsonl`.
`cheatsheet_queries.py` re-runs every query in `notes/2026-10-04-prismql-cheatsheet.md`.
