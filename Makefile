.PHONY: sync serve repl smoke village village-embed embed-deps
sync:            ## install the language (editable, from ../../vibes/prismql)
	uv sync
serve:           ## the query server on every corpus in prismql.toml
	uv run prismql-server --config prismql.toml
repl:            ## interactive queries on the default corpus
	uv run prismql --config prismql.toml
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
	  --id id --time created_at --sort event_index
embed-deps:      ## the embedding model stack (torch; large) for --embed
	uv pip install sentence-transformers
village-embed:   ## same, with an `emb` column (multilingual model; needs embed-deps)
	uv run python prepare/village.py
	uv run prismql ingest table data/village_events.parquet data/village.parquet \
	  --id id --time created_at --sort event_index \
	  --embed text --model paraphrase-multilingual-MiniLM-L12-v2
