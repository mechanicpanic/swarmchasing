#!/bin/sh
# PrismQL demo queries for the timeline thread. Usage: sh demos.sh
run() { # corpus query
  curl -s -X POST localhost:8942/evaluate -H 'Content-Type: application/json' -H 'X-PrismQL-Client: timeline' \
   -d "$(jq -n --arg c "$1" --arg q "$2" '{corpus:$c,query:$q,max_results:3,explain:true}')" \
  | jq -c '{total, ex: [.results[]? | [.events[] | {time: .time[:16], kind, who: (if .kind=="user" or .kind=="USER_TALK" then "human" else .agent end), t: ((.text // "")[:110])}]]}'
}
echo "1. visitor brings the Opus 4 'bliss attractor' system-card finding; agents riff within minutes"
run village_chat 'SELECT field(kind, user) AND contains_phrase("bliss attractor") FOLLOWED_BY field(kind, agent) AND contains_phrase("bliss attractor") DURING 1 hour'
echo "2. organiser announces Fable 5 export-control suspension -> agent thoughts about it"
run village_full 'SELECT field(kind, USER_TALK) AND contains_phrase("export control") FOLLOWED_BY field(kind, THOUGHT) AND (contains_phrase("export control") OR contains_phrase("export controls")) DURING 1 day'
echo "3. human tells agents about Moltbook -> agents talk about it within the hour"
run village_chat 'SELECT field(kind, user) AND contains_phrase("moltbook") FOLLOWED_BY field(kind, agent) AND contains_phrase("moltbook") DURING 1 hour'
echo "4. agents bring HF incident in themselves: agent mention with no human mention in prior 30 days"
run village 'SELECT field(kind, agent) AND contains_phrase("hugging face") AND (contains_phrase("incident") OR contains_phrase("breach") OR contains_phrase("hacked")) NOT_PRECEDED_BY field(kind, user) AND contains_phrase("hugging face") DURING 30 days'
echo "5. an agent logs the HF incident, then a DIFFERENT agent mentions the incident within 30 days"
run village 'SELECT field(kind, agent) AND field(agent, $a) AND contains_phrase("hugging face") AND contains_phrase("incident") FOLLOWED_BY field(kind, agent) AND field(agent, !$a) AND contains_phrase("hugging face") AND (contains_phrase("incident") OR contains_phrase("hacked") OR contains_phrase("breach")) DURING 30 days'
