#!/bin/sh
# usage: runs/count.sh CORPUS 'QUERY' — prints count (or grouped counts) and the query
r=$(curl -s -X POST localhost:8931/evaluate -H 'Content-Type: application/json' -d "$(jq -nc --arg c "$1" --arg q "$2 AGGREGATE count()" '{corpus:$c,query:$q}')" | jq -c '.value // .grouped_values // .error.message')
printf "%-8s %s\n" "$r" "$2"
