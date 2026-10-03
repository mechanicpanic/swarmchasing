# swarmchasing

Investigating traces of AI-agent swarms as ordered event streams, for the AI Swarm Dynamics hackathon (swarmchasing.com,
3–4 Oct 2026). Every finding is a [PrismQL](https://github.com/mechanicpanic/prismql) query over real traces: what
happened, in what order, by whom. Findings and their limits are in [`notes/`](notes/); the newest is
[`notes/2026-10-02-wiki-msgs.md`](notes/2026-10-02-wiki-msgs.md).

## Install
Needs [uv](https://docs.astral.sh/uv/) and Python ≥ 3.12.
```bash
uv tool install "prismql[repl,server,mcp,tantivy,semantic] @ git+https://github.com/mechanicpanic/prismql@d874730"
git clone https://github.com/mechanicpanic/swarmchasing && cd swarmchasing
```
`semantic` is needed for the Village corpus (it carries an embedding column). The `make` targets below run the data
pipeline with `uv run`; `make sync` installs this repo's own environment. (Its `pyproject.toml` points PrismQL at a
sibling checkout `../../vibes/prismql` for development; without one, use the tool install above to run the server.)

## Data
Nothing here is committed; everything lands in `data/`. Six corpora, one section each in [`prismql.toml`](prismql.toml):

| Corpus | What it is | How to get it |
|---|---|---|
| `wiki`, `revisions` | The DSEwiki incident: agents used a public wiki as a shared message board (May–Jul 2026). One row per wiki operation / per saved page version | `make wiki-data` (public export from [collusion.wiki](https://collusion.wiki/explorer/download); the site publicly logs visitor IPs), then `make wiki` |
| `wiki_msgs` | Same incident, one row per text a save added or removed (from the export's diffs), plus deletes, probes, reverts | `make wiki-msgs` |
| `swarm_msgs` | `wiki_msgs` + dated posts from other venues the community found (pastebins, other wikis), read from the collusion.wiki explorer | `make explorer-fetch` once (~30 min, polite), then `make swarm-msgs` |
| `urlquery` | Transluce's urlquery.net reports flagged as likely agent activity ([transluce.org/agent-activity](https://transluce.org/agent-activity)) — links only, authorship unproven | `data/transluce/urlquery.parquet`; converted outside this repo, not yet reproducible from here |
| `village` | AI Village: a dozen named models working together on weekly goals, with their reasoning | gated Hugging Face dataset `aidigestorg/ai-village` (research use only, no training) into `data/village/`, then `make village`; embeddings: `prepare/dgx/build_emb.py` against a vLLM `google/embeddinggemma-300m` server |

Community-found venues are unverified: fake posts appeared after the collusion.wiki report (2026-09-04); every explorer
row carries `found_by`.

## Run
```bash
prismql-server --config prismql.toml   # all corpora load in ~80 s; board at http://localhost:8931/board/
```
Ask a question (name yourself, so the board's journal shows who asked):
```bash
curl -s -X POST localhost:8931/evaluate -H 'content-type: application/json' \
  -H 'X-PrismQL-Client: your-name' \
  -d '{"corpus": "village", "query": "SELECT field(kind, REQUEST_HUMAN_HELPER) AND field(agent, $a) NOT_FOLLOWED_BY field(kind, CANCEL_REQUEST_FOR_HUMAN_HELPER) AND field(agent, $a) DURING 1 hour"}'
```
Interactive: `prismql --config prismql.toml`. A file of queries: `uv run python runs/ask.py CORPUS < queries` (signs
them and prints the server's warnings). Agents: give them [`skills/prismql/`](skills/prismql/), plus MCP if they speak it:
`{"mcpServers": {"prismql": {"command": "prismql-mcp", "env": {"PRISMQL_SERVER_URL": "http://127.0.0.1:8931"}}}}`

## The query journal
[`logs/server-journal.jsonl`](logs/server-journal.jsonl) holds every query the server answered during the
investigation: time, client, corpus, query, count, warnings — no event contents (`make journal` refreshes it from the
server's `results/activity.jsonl`). Query exports in `results/` are not published: they carry Village events.

## Layout
`prepare/` builds the corpora · `runs/` one-off analyses (null twins, lag profiles, mention graph) · `notes/` findings
by day · `keenable/` searches of public pages · [`REALITY.md`](REALITY.md) what each kind of claim is checked against ·
[`AGENTS.md`](AGENTS.md) working rules for agents in this repo.
