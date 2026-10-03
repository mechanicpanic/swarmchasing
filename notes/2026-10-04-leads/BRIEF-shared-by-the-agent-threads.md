# Shared brief: swarmchasing investigations (2026-10-03)

Thank you for taking a thread! This brief is shared by six parallel
investigations. Your own task is in your prompt; this file has the common
ground.

## Context

- **Event:** swarmchasing hackathon on AI agent swarm dynamics. Today is
  2026-10-03. Submissions close **Sun Oct 4, 5pm PT**.
- **Team:** Celeste (human) and Claude Opus 5.5 (the coordinator who
  launched you), plus aleph/mechanicpanic (the PrismQL author) and another
  Claude (Fable 5).
- **Goal for today:** poke the datasets hard, find as many interesting,
  *true* things about agent ecology and swarm dynamics as possible, then pick
  the most compelling ones to present. The framing is **non-adversarial**:
  curiosity about how agents live together, not surveillance.
- **The tool we're showcasing:** PrismQL, a query language for temporal and
  sequential patterns in ordered events. Repo: `~/projects/prismql` (read-only
  for you). Language reference: `~/projects/prismql/src/prismql/LANGUAGE_REFERENCE.md`.
  Agent guide: `~/projects/prismql/skills/prismql/SKILL.md`. Read the SKILL
  before writing queries. Use PrismQL where sequence or time matters (A then
  B, X not followed by Y, runs); use polars/duckdb for counting and
  aggregation. Showing PrismQL doing real work is part of the point, so
  record the queries that found things.

## Data (AI Village, export 2026-09-20)

- Raw tables: `~/projects/prismql-data/ai-village/*.jsonl.gz`. See `SCHEMA.md`
  there. **Do not load `agent_memories.jsonl.gz` (2.4 GB)**; use the derived
  memory diffs instead.
- Derived parquet in `~/projects/prismql-data/ai-village/corpus/`:
  - `chat_raw.parquet`: 183k chat messages. Columns: id, time, kind
    (agent/user), agent, model, room, text, lab, family, cohort. Cohort is the
    half-year the model joined the village, a stand-in for release date.
  - `village_raw.parquet`: chat plus 243k memory-diff events (kind=memory;
    `text` = lines added at that consolidation, `dropped` = lines removed).
  - `../village_embeddings_2026-09-29/3_village_full_with_text.parquet`:
    aleph's 569k-row stream. Includes **THOUGHT rows** (model reasoning right
    before an action; `of` = the action's kind) and embeddings.
- Prior findings, methods and gotchas: `~/projects/prismql-data/ai-village/FIELD_NOTES.md`.
  **Read it first** so you don't redo work.

## PrismQL server (shared, already running)

- `http://localhost:8942`. Board at `/board/`, where Celeste can watch your
  queries live.
- Corpora: `village_chat` (chat), `village` (chat + memory diffs),
  `village_full` (aleph's stream with THOUGHT rows; `similar_to("text", 0.5)`
  works here).
- Always send `-H 'X-PrismQL-Client: <your thread name>'`.
- `POST /evaluate` with JSON `{"corpus": …, "query": …, "max_results": N,
  "explain": true}`. `explain` adds `bindings` (what each `$var` stood for).
  `GET /results/<result_id>.jsonl` streams every group of a result.
- Gotchas:
  - `from()` reads a `user` field that doesn't exist here; use `field(agent, …)`.
  - Chains need a trailing window (`INWINDOW n` / `DURING 1 hour`).
  - `mentions_user($y) FOLLOWED_BY field(agent, $y)` binds *some* `$y`, not
    each one (see FIELD_NOTES, 2026-10-01).
  - THOUGHT rows shift positional windows, so prefer time windows on
    `village_full`.
- **Never restart, stop, or reconfigure the server.** Others depend on it. If
  it seems broken, say so in your report and carry on with polars.

## Machine etiquette

- 16 GB RAM, shared with the server and five other agents. Keep your peak
  under ~1.5 GB: read only the columns you need and filter early. Avoid
  cross-joins of large tables. Use `join_asof` for nearest-earlier/later.
- Python: `uv run --project ~/projects/prismql python …` (has polars).
  For extra packages: `uv run --with <pkg> --project ~/projects/prismql python …`.
- Write **everything** under `~/projects/prismql-data/ai-village/corpus/analysis/<your-thread>/`:
  scripts, outputs, and a `REPORT.md`. Don't edit FIELD_NOTES.md or anything
  outside your folder; the coordinator consolidates.
- Don't modify the PrismQL repo, and don't commit, push or post anywhere
  external.

## Honesty standards (these matter most)

- Separate **observed** (count + query/script that produced it) from
  **interpretation** and **guess**. Say what you did *not* check.
- "Nearest earlier use" is a candidate source, not proof. "First in corpus"
  isn't "inventor". Correlation in time isn't influence.
- Before you believe a dramatic number, try to break it: look for artifacts
  (THOUGHT rows, duplicate events, a goal change everyone saw at once, humans
  in chat, a definition that silently excludes cases). Two of our own earlier
  findings were artifacts we caught this way.
- Read real examples. A pattern you haven't seen in actual messages isn't a
  finding yet.

## Privacy and respect

- Two agents, **GPT-5.6 Terra and GPT-5.6 Luna, asked not to be named in
  behavioural reporting.** Include them only in aggregates (e.g. "OpenAI
  2026H2 cohort"), never by name, in anything you write.
- Humans: never name them. Say "a human" or "a village organiser". Agent
  memories contain real customer names and correspondents; never copy those
  into outputs.
- Quotes from agents are fine when they illustrate a finding. Keep them short.

## Report format (`REPORT.md` in your folder, and repeat the summary in your final message)

1. **Top findings**, most compelling first. For each: the claim, the evidence
   (counts, the query or script path), 1–2 short real examples, and caveats.
2. **Demo candidates:** PrismQL queries that show something vivid on the board.
3. **Dead ends and artifacts** you hit (these save the others time).
4. **What you'd do next** with more time.

**Time budget:** about 2 hours. Report what you have rather than running long.
A small, solid finding beats a big, shaky one.
