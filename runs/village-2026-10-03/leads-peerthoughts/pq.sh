#!/bin/sh
# usage: pq.sh '<json body>'
curl -s -X POST localhost:8942/evaluate -H 'Content-Type: application/json' -H 'X-PrismQL-Client: peer-thoughts' -d "$1"
