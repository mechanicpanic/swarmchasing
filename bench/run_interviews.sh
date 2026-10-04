#!/usr/bin/env bash
# Resume each PrismQL-arm run with the same interview prompt, one after another.
set -u
export PATH=/usr/bin/core_perl:$PATH MBAB_MIN_RUNTIME_FRACTION=0
B="--build-arg WITH_PRISMQL=1 --build-arg CLAUDE_VERSION=2.1.287"
n=90
for R in runs/*_claude_*_r[123]_blind-30-prismql_* runs/*_codex_*_r[123]_blind-30-prismql_*; do
  n=$((n+1)); a=$(basename "$R" | cut -d_ -f2)
  if [ "$a" = claude ]; then m=claude-opus-5-5; else m=gpt-5.6-sol; fi
  RESUME_FROM="$R" IMAGE=mbab-prismql MBAB_BUILD_ARGS="$B" CONFIG=interview sandbox/docker/run_trial.sh "$a" "$m" "$n"
  echo "=== interview $n $a from $(basename "$R") done $(date -u +%FT%TZ)"
done
