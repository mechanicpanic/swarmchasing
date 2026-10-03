.PHONY: sync serve repl smoke check village village-embed embed-deps wiki-msgs explorer-fetch swarm-msgs
sync:            ## install the language (editable, from ../../vibes/prismql)
	uv sync
serve:           ## the query server on every corpus in prismql.toml
	uv run prismql-server --config prismql.toml
repl:            ## interactive queries on the default corpus
	uv run prismql --config prismql.toml
check:           ## the gate: full ruff + format on the data pipeline, pyflakes on exploratory runs, smoke if the server is up
	uvx ruff check prepare
	uvx ruff format --check prepare
	uvx ruff check --select F runs
	@if curl -s -m 2 localhost:8931/health >/dev/null; then $(MAKE) -s smoke; else echo "server on 8931 is down: smoke skipped"; fi
smoke:           ## three questions against a running server
	@curl -s localhost:8931/health; echo
	@curl -s -X POST localhost:8931/evaluate -H 'Content-Type: application/json' -d '{"query":"SELECT field(event_type, delete) AND field(page,$$p) FOLLOWED_BY field(event_type, save) AND field(page,$$p) DURING 10 minutes AGGREGATE count()"}'; echo
	@curl -s -X POST localhost:8931/evaluate -H 'Content-Type: application/json' -d '{"query":"SELECT field(event_type, save) AND field(page,$$p) AND field(label,$$a) FOLLOWED_BY field(event_type, delete) AND field(page,$$p) FOLLOWED_BY field(event_type, save) AND field(page,$$p) AND field(label,$$a) DURING 1 day AGGREGATE count()"}'; echo

# --- AI Village: export (data/village/, gated) → one stream the server reads.
# Layer 1 split: joins and column choice here (prepare/village.py), the
# canonical stream (position, id, time, emb) by the language's own ingest.
village:         ## data/village/*.jsonl.gz → data/village.parquet (no embeddings)
	uv run python prepare/village.py
	uv run prismql ingest table data/village_events.parquet data/village.parquet \
	  --id id --time created_at --sort seq
embed-deps:      ## the embedding model stack (torch; large) for --embed
	uv pip install sentence-transformers
village-embed:   ## same, with an `emb` column (multilingual model; needs embed-deps)
	uv run python prepare/village.py
	uv run prismql ingest table data/village_events.parquet data/village.parquet \
	  --id id --time created_at --sort seq \
	  --embed text --model paraphrase-multilingual-MiniLM-L12-v2

# --- collusion.wiki: what each save added or removed (hunks), plus deletes / probes / reverts.
wiki-msgs:       ## export (../prismql-research/hackathon/swarmchasing/data) → data/wiki_msgs.parquet
	uv run python prepare/wiki_msgs.py
	uv run prismql ingest table data/wiki_msgs_rows.parquet data/wiki_msgs.parquet \
	  --id id --time time --sort seq
explorer-fetch:  ## collusion.wiki explorer pages of venues not in the download → data/collusion_explorer/ (network, cached, ~30 min cold)
	uv run python prepare/explorer_sites.py fetch
swarm-msgs: wiki-msgs  ## wiki_msgs + explorer rows with a time → data/swarm_msgs.parquet (needs explorer-fetch once)
	uv run python prepare/explorer_sites.py parse
	uv run python prepare/swarm_msgs.py
	uv run prismql ingest table data/swarm_msgs_rows.parquet data/swarm_msgs.parquet \
	  --id id --time time --sort seq
