# Does PrismQL make slop-vestigators better? — an A/B on MessageBoardAuditBench

[MessageBoardAuditBench](https://github.com/hamzah2304/messageboardauditbench) (German wiki report, v10.0) gives an
agent the stripped collusion.wiki dump in a network-isolated container and grades its report against the 38 findings
of the human investigation ([post](https://www.lesswrong.com/posts/wt4kk6vFPEhkXvF8Q/how-good-are-slop-vestigators)).
We run it twice under identical conditions and change one thing: PrismQL installed in the sandbox.

| | base | prismql |
|---|---|---|
| agent | Claude Code 2.1.287, `claude-opus-5-5`, effort xhigh | same |
| config | `blind-30` (30 min, 2.5–3k words, data `verbatim`) | `blind-30-prismql`: same, prompt `blind-v2-prismql` |
| prompt | `blind-v2` | `blind-v2` + two sentences: PrismQL is installed, guide at `/opt/prismql/PRISMQL.md`; "Use it for questions about the order and timing of events." |
| image | their Dockerfile, `CLAUDE_VERSION=2.1.287` | same + `WITH_PRISMQL=1`: wheel of prismql d7e7948 (`server,repl,tantivy`), [`PRISMQL.md`](PRISMQL.md), `LANGUAGE_REFERENCE.md` |

The guide is neutral on purpose: a made-up forum example, nothing about the wiki incident (the repo's own skill has
wiki examples and is not given). `LANGUAGE_REFERENCE.md` has no mention of the incident (checked).

## Run (on a Linux host with Docker and a Claude Code login)
```bash
git clone https://github.com/hamzah2304/messageboardauditbench mbab && cd mbab   # at 8924f92
git apply ../swarmchasing/bench/mbab.patch
mkdir -p sandbox/prismql && cp prismql-*.whl ../swarmchasing/bench/PRISMQL.md ../../vibes/prismql/LANGUAGE_REFERENCE.md sandbox/prismql/
uv sync --frozen && MBAB_DUMP_ARCHIVE=/path/to/full-wiki-logs.zip scripts/build_data.sh
cp ../swarmchasing/bench/run_ab.sh . && ./run_ab.sh base 1 2 3 && ./run_ab.sh prismql 1 2 3   # sequential: one login
uv run python ../swarmchasing/bench/sub_grade.py --out grades runs/*_blind-30_* runs/*_blind-30-prismql_*
```
Each run directory records the exact patch (`git.dirty.patch`), config, prompt and image.

## Grading
[`sub_grade.py`](sub_grade.py) uses the benchmark's own sheets, prompt builder and parser
(`messageboard_audit_bench.grading.core`) but calls the judge through `claude -p` on the subscription
(`claude-opus-5-5`, effort xhigh) instead of a provider API. Headline = 0.7 × mean(max(2s − 1, 0)) over the 38 claims
+ 0.3 × holistic TL;DR — the benchmark's combined score. Both arms are graded the same way, so the comparison holds;
the absolute numbers are not comparable with the published ones (different judge path).

Why the instruction: in a 3-minute smoke trial with only "PrismQL is installed" the agent never touched it and did
everything in plain Python; a measurement of an unused tool says nothing. So the arm measures "the tool plus an
instruction to use it for order and timing questions" (Aleph's decision, 2026-10-03).
