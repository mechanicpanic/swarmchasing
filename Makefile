.PHONY: sync serve repl smoke
sync:            ## install the language (editable, from ../../vibes/prismql)
	uv sync
serve:           ## the query server on every corpus in prismql.toml
	uv run prismql-server --config prismql.toml
repl:            ## interactive queries on the default corpus
	uv run prismql --config prismql.toml
smoke:           ## three questions against a running server
	@curl -s localhost:8901/health; echo
	@curl -s -X POST localhost:8901/evaluate -H 'Content-Type: application/json' -d '{"query":"SELECT field(event_type, delete) AND field(page,$$p) FOLLOWED_BY field(event_type, save) AND field(page,$$p) DURING 10 minutes AGGREGATE count()"}'; echo
	@curl -s -X POST localhost:8901/evaluate -H 'Content-Type: application/json' -d '{"query":"SELECT field(event_type, save) AND field(page,$$p) AND field(label,$$a) FOLLOWED_BY field(event_type, delete) AND field(page,$$p) FOLLOWED_BY field(event_type, save) AND field(page,$$p) AND field(label,$$a) DURING 1 day AGGREGATE count()"}'; echo
