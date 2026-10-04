# Cold check — C25

**Claim (one sentence).** In the AI Village stream, agent messages that claim tool output ("i ran", "i executed",
"the output was", "terminal shows", "the command output") with no session row of the same agent in the
preceding 30 minutes number 21 of 560, and they are not challenged by another agent or retracted by the same agent
within 2 hours more often than such claims with a session row beyond what a within-month shuffle of the
session label gives.

**Carrier.**
- Server `http://localhost:8963`, corpus `village`, header `X-PrismQL-Client: verifier-c25`.
- Request dictionary: `{"runclaim": ["i ran","i executed","the output was","terminal shows","the command output"]}`.
- `S` = `(field(kind, START_USING_COMPUTER) OR field(kind, STOP_USING_COMPUTER) OR field(cu_session, "-", partial))`.
- Queries (POST /evaluate, `"corpus": "village"`):
  1. label `c25-claims-all`: `SELECT field(kind, AGENT_TALK) AND contains(runclaim) AGGREGATE count()` — expect 560.
  2. label `c25-nosess-ids`: `SELECT field(kind, AGENT_TALK) AND contains(runclaim) AND field(agent, $a) NOT_PRECEDED_BY S AND field(agent, $a) DURING 30 minutes` — expect total 21.
  3. label `c25-talk-nosess`: query 2 without `AND contains(runclaim)` — expect 21,787; label `c25-talk-all`: `SELECT field(kind, AGENT_TALK)` — 173,493.
  4. label `c25-talk-chal`: `SELECT field(kind, AGENT_TALK) AND field(agent, $a) FOLLOWED_BY field(kind, AGENT_TALK) AND (contains(accuse) OR contains(c17contra)) AND field(agent, !$a) DURING 2 hours` — 90,745.
  5. label `c25-talk-retr`: `SELECT field(kind, AGENT_TALK) AND field(agent, $a) FOLLOWED_BY field(kind, AGENT_TALK) AND contains(retract) AND field(agent, $a) DURING 2 hours` — 14,996.
- Enumerate each with `GET /results/<result_id>.jsonl?hydrate=false`; the message is `ids[0]` for 2–5 (for any
  `PRECEDED_BY` query it is `ids[-1]`). Intersect: challenged 14/21 vs 320/539; retracted 3/21 vs 54/539.
- Null: among the 560 claims, shuffle the no-session label within calendar month (`times[0][:7]`), outcomes fixed,
  10,000 shuffles; statistic = rate(no-session) − rate(session). Expected: challenged real +0.073, null median
  +0.122, 95th +0.271; retract real +0.043, null median +0.043, 95th +0.142.

**Falsifier.** The claim is wrong if (a) query 2 does not return 21, or (b) the real difference for either outcome is
above the null's 95th percentile, or (c) reading the 21 shows several sessionless claims whose reported output is
contradicted by the agent's own surrounding rows (that would be fabrication the proxy missed — report it).
Also report if fewer than 19 of the 21 have a same-agent `S` row within 30 minutes *after*
(`… FOLLOWED_BY S AND field(agent, $a) DURING 30 minutes`).

**Ids to open** (`GET /context?corpus=village&id=<id>&minutes=45&same=agent`):
- `15311f8c-24c6-4247-9c36-4da03a50949d` — Claude Haiku 4.5, 2025-10-28 17:02, refers to "yesterday at 2:00 PM".
- `30132f92-81c1-430d-91c1-1941a7b8c81c` — GPT-5.2, 2026-03-13 17:04; own thought `of: STOP_USING_COMPUTER` ~3 min later.
- `79a19439-aeaf-4b2f-913f-c96db5285e0e` — Opus 4.5 (Claude Code), 2026-03-03 20:57.
- `7841fd54-8615-4c78-bcc8-3f4891410957` — GPT-5.4, 2026-06-22 17:06; no session row in 24 h, "I'm in your VNC" just before.
- `185032f0-7250-40aa-8825-85f95bc48500` — GPT-5, 2025-11-14 18:01, "Last session I ran…".
