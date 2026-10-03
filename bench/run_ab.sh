#!/usr/bin/env bash
# usage: run_ab.sh base|prismql REPLICATES...  — sequential 30-minute trials of one arm (Opus 5.5, Claude Code 2.1.287)
set -u
export PATH=/usr/bin/core_perl:$PATH
arm=$1; shift
for r in "$@"; do
  if [ "$arm" = prismql ]; then
    IMAGE=mbab-prismql MBAB_BUILD_ARGS="--build-arg WITH_PRISMQL=1 --build-arg CLAUDE_VERSION=2.1.287" CONFIG=blind-30-prismql \
      sandbox/docker/run_trial.sh claude claude-opus-5-5 "$r"
  else
    IMAGE=mbab-base MBAB_BUILD_ARGS="--build-arg CLAUDE_VERSION=2.1.287" CONFIG=blind-30 \
      sandbox/docker/run_trial.sh claude claude-opus-5-5 "$r"
  fi
  echo "=== $arm r$r done $(date -u +%FT%TZ)"
done
