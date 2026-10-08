.PHONY: demo findings null-demo review village-data demo-village findings-village cheatsheet sync serve wiki-data wiki journal urlquery repl smoke check village village-embed embed-deps wiki-msgs explorer-fetch swarm-msgs village-memories memory
# Two ways to run. Aleph's loop: the language editable from the sibling checkout, everything through this project's
# environment. A fresh clone: the language from `uv tool install` (README), the pipeline's two libraries per command.
ifneq ($(wildcard ../../vibes/prismql),)
PY  := uv run python
PQ  := uv run prismql
PQS := uv run prismql-server
PYQ := uv run python
else
PY  := uv run --no-project --with "polars>=1.44,<2" --with "pyarrow>=15" python
PQ  := prismql
PQS := prismql-server
PYQ := uv run --no-project --with "prismql @ git+https://github.com/mechanicpanic/prismql@0100335" --with "polars>=1.44,<2" --with "pyarrow>=15" python
endif
demo: wiki-data wiki wiki-msgs  ## first run on a fresh clone: the public wiki export → three corpora → server + board on :8931
	$(PQS) --config prismql.demo.toml $(if $(PORT),--port $(PORT))
findings:        ## with the server up: replay the wiki findings' queries onto the board, labelled, signed swarmchasing-findings
	PRISMQL_CLIENT=swarmchasing-findings PRISMQL_URL=http://localhost:$(or $(PORT),8931) $(PY) runs/report_claims.py
null-demo:       ## one null twin: "another name confirms on the same page within 30 min" — real count vs whole saves shuffled within page and day
	$(PYQ) runs/null_twin.py "SELECT field(kind, add) AND contains(confirmed) AND field(label, \$$a) AND field(page, \$$p) FOLLOWED_BY field(kind, add) AND contains(confirmed) AND field(label, !\$$a) AND field(page, \$$p) DURING 30 minutes" \
	  --data data/wiki_msgs.parquet --type-field kind --shuffle add --unit rev --key day,page --distinct-last --n $(or $(N),50) --dicts '{"confirmed": ["confirmed"]}'
village-data:    ## the three files of the AI Village export the pipeline reads (~700 MB; gated: accept the terms at huggingface.co/datasets/aidigestorg/ai-village, then `hf auth login`)
	uvx --from huggingface_hub hf download aidigestorg/ai-village --repo-type dataset --include agents.jsonl.gz --include events.jsonl.gz --include village-transcript.json --local-dir data/village
demo-village: wiki-data wiki wiki-msgs village-data village  ## the demo plus AI Village: server + board on :8931 (Village loads in ~1 min)
	$(PQS) --config prismql.demo-village.toml $(if $(PORT),--port $(PORT))
findings-village: ## with demo-village up: the Village findings' queries onto the board, labelled, signed swarmchasing-findings
	PRISMQL_CLIENT=swarmchasing-findings PRISMQL_URL=http://localhost:$(or $(PORT),8931) $(PY) runs/village_findings.py
cheatsheet:      ## with demo-village up: 14 teaching queries, one per construct of the language, on the Village corpus
	PRISMQL_CLIENT=cheatsheet PRISMQL_URL=http://localhost:$(or $(PORT),8931) $(PY) runs/village_cheatsheet.py
review:          ## with a demo server up: the review (mark ✔/✘/?) and trails app on :8960, with example queues
	PRISMQL_URL=http://localhost:$(or $(PORT),8931) PRISMQL_CONFIG=$(or $(CONFIG),$(if $(wildcard data/village.parquet),prismql.demo-village.toml,prismql.demo.toml)) \
	  uv run --no-project --with fastapi --with uvicorn --with "polars>=1.44,<2" python tools/review/review_server.py --port $(or $(REVIEW_PORT),8960) & \
	  srv=$$!; REVIEW_URL=http://localhost:$(or $(REVIEW_PORT),8960) PRISMQL_URL=http://localhost:$(or $(PORT),8931) $(PY) runs/review_seed.py; \
	  echo "review: http://localhost:$(or $(REVIEW_PORT),8960)/  trails: http://localhost:$(or $(REVIEW_PORT),8960)/trails"; wait $$srv
sync:            ## install the language (editable, from ../../vibes/prismql)
	uv sync
serve:           ## the query server on every corpus in prismql.toml
	$(PQS) --config prismql.toml
repl:            ## interactive queries on the default corpus
	$(PQ) --config prismql.toml
check:           ## the gate: full ruff + format on the data pipeline, pyflakes on exploratory runs, smoke if the server is up
	uvx ruff check prepare
	uvx ruff format --check prepare
	uvx ruff check --select F runs
	@if curl -s -m 2 localhost:8931/health >/dev/null; then $(MAKE) -s smoke; else echo "server on 8931 is down: smoke skipped"; fi
smoke:           ## three questions against a running server
	@curl -s localhost:8931/health; echo
	@curl -s -X POST localhost:8931/evaluate -H 'Content-Type: application/json' -H 'X-PrismQL-Client: smoke' -d '{"query":"SELECT field(event_type, delete) AND field(page,$$p) FOLLOWED_BY field(event_type, save) AND field(page,$$p) DURING 10 minutes AGGREGATE count()"}'; echo
	@curl -s -X POST localhost:8931/evaluate -H 'Content-Type: application/json' -H 'X-PrismQL-Client: smoke' -d '{"query":"SELECT field(event_type, save) AND field(page,$$p) AND field(label,$$a) FOLLOWED_BY field(event_type, delete) AND field(page,$$p) FOLLOWED_BY field(event_type, save) AND field(page,$$p) AND field(label,$$a) DURING 1 day AGGREGATE count()"}'; echo

# --- AI Village: export (data/village/, gated) → one stream the server reads.
# Layer 1 split: joins and column choice here (prepare/village.py), the
# canonical stream (position, id, time, emb) by the language's own ingest.
village:         ## data/village/*.jsonl.gz → data/village.parquet (no embeddings)
	$(PY) prepare/village.py
	$(PQ) ingest table data/village_events.parquet data/village.parquet \
	  --id id --time created_at --sort seq
embed-deps:      ## the embedding model stack (torch; large) for --embed
	uv pip install sentence-transformers
village-embed:   ## same, with an `emb` column (multilingual model; needs embed-deps)
	$(PY) prepare/village.py
	$(PQ) ingest table data/village_events.parquet data/village.parquet \
	  --id id --time created_at --sort seq \
	  --embed text --model paraphrase-multilingual-MiniLM-L12-v2

# --- AI Village: agents' memory files, one row per rewrite (research use only; stays local).
village-memories: ## data/village/agent_memories.jsonl.gz → data/village_memories.parquet + _index.parquet (~70 s, ~1.2 GB peak RAM)
	$(PY) prepare/village_memories.py
memory:          ## the memory-file reader (versions, diffs, search, chat before each rewrite) on :8970; needs village-memories
	uv run --no-project --with fastapi --with uvicorn --with "polars>=1.44,<2" --with "pyarrow>=15" \
	  python tools/memory/memory_server.py --port $(or $(MEMORY_PORT),8970)

# --- collusion.wiki: the public export (https://collusion.wiki/explorer/download; the site publicly logs visitor IPs).
WIKI_FILES = events.jsonl.gz revisions.jsonl.gz pages.jsonl.gz labels.jsonl.gz records.jsonl.gz links.jsonl.gz \
	manifest.json.gz other-wikis.json.gz shortener-logs.json.gz site-coverage.csv coverage-gaps.csv
wiki-data:       ## download the export into data/collusion_wiki/ (skips files already there)
	mkdir -p data/collusion_wiki
	for f in $(WIKI_FILES); do [ -s data/collusion_wiki/$$f ] || curl -fsSL -o data/collusion_wiki/$$f https://collusion.wiki/explorer/download/$$f; done
wiki:            ## export → data/collusion_wiki_events.jsonl + data/collusion_wiki_revisions.jsonl (corpora wiki, revisions)
	$(PY) prepare/wiki_events.py
urlquery:        ## Transluce release zip (downloaded by hand from https://transluce.org/agent-activity) → data/transluce/urlquery.parquet; make urlquery ZIP=path/to/urlquery-agent-activity-….zip
	@test -n "$(ZIP)" || { echo "usage: make urlquery ZIP=path/to/urlquery-agent-activity-….zip"; exit 2; }
	mkdir -p data/transluce
	$(PY) prepare/urlquery.py "$(ZIP)"
	$(PQ) ingest table data/transluce/urlquery.csv data/transluce/urlquery.parquet --id id --time time --sort time
journal:         ## the server's query journal → logs/server-journal.jsonl (no event contents; local paths made relative)
	mkdir -p logs
	jq -c '.path |= (if type == "string" then sub("^.*/swarmchasing/"; "") else . end)' results/activity.jsonl > logs/server-journal.jsonl

# --- collusion.wiki: what each save added or removed (hunks), plus deletes / probes / reverts.
wiki-msgs:       ## the export in data/collusion_wiki/ → data/wiki_msgs.parquet
	$(PY) prepare/wiki_msgs.py
	$(PQ) ingest table data/wiki_msgs_rows.parquet data/wiki_msgs.parquet \
	  --id id --time time --sort seq
explorer-fetch:  ## collusion.wiki explorer pages of venues not in the download → data/collusion_explorer/ (network, cached, ~30 min cold)
	$(PY) prepare/explorer_sites.py fetch
swarm-msgs: wiki-msgs  ## wiki_msgs + explorer rows with a time → data/swarm_msgs.parquet (needs explorer-fetch once)
	$(PY) prepare/explorer_sites.py parse
	$(PY) prepare/swarm_msgs.py
	$(PQ) ingest table data/swarm_msgs_rows.parquet data/swarm_msgs.parquet \
	  --id id --time time --sort seq
