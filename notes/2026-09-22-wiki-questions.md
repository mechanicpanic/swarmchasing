# 2026-09-22 — three questions on the wiki stream (server 8931, null twin `runs/null_twin.py`)

Null twin = save times permuted within a key (label unless noted), n runs, same query re-run inline.

| # | Question (PrismQL) | Real | Null median / 95th | Verdict |
|---|---|---|---|---|
| smoke | `delete($p) FOLLOWED_BY save($p) DURING 10 minutes` | 25 | 19 / 24 (n=50) | clears 95th, barely |
| Q1 | `probe($n:ip16) FOLLOWED_BY save($n) DURING 1 hour` | 44 of 101 probes | 44 / 44 (key=ip16, n=200) | **uninformative**: saves from the probing /16s are so dense that any permutation leaves one within 1 h. Count is a density measure, not a sequence. |
| Q3 | `save(relay-coordination,$a) FOLLOWED_BY save(loop-chain-infrastructure,$a) DURING 1 hour` | 346 | 486 / 526 (n=100) | **below null**: a label that writes coordination pages moves to infrastructure pages *less* than its own activity level predicts. Reads as role separation between names. |

Q1 instances (`results/q1_probe_then_save_1h-3e961f.jsonl`): 25 of 44 are one actor, `AgentDataHelperX` on 52.87, probe → relay-coordination write with gaps clustered 450–520 s (a rhythm, possibly a scripted probe-then-write loop). Remaining 19 spread over 20.x Azure ranges, gaps 35 s – 50 min, writes to source-cache and probe-test families.
Right follow-up for Q1: not a count but the gap distribution under a probe-time shuffle (`--shuffle probe --key ip16`); needs the script to report gap quantiles, not only counts.

Other counts (no null yet): delete → save same *family* 10 min: 90. Same page saved by two different labels within 5 min: 5,667 (the relay cluster's handoffs; a sequence question here needs `!$a` plus a family restriction to mean anything).

Language note → prismql repo: an unquoted hyphenated value (`field(page_family, relay-coordination)`) fails with `token recognition error at: '-'`; quoted (`"relay-coordination"`) works. Either accept bare hyphens or make the 422 say "quote it".

## 2026-09-24 — leadership / coordination in the wiki (`runs/wiki_coordination.py`)
Identity is a label (1,332 names with one revision), so no @-graph. Traces instead:
- Addressing: messages name other handles ("May10OAI ping … Please relay exact R5 field/value"), but flatly — the most-named handle (Agent0) appears in 75 of 13,703 messages. No hub agent.
- Hub pages (stigmergy): dse~WillkommenImWiki (the welcome page) written by 342 labels in 2,327 revisions, 2026-06-18 → 07-02; StartSeite 293 labels; TestSeite 190. Coordination runs through shared pages, not through a person.
- Broadcast bursts: one message ("Loop predicted child raw investor", jqp.vercel.app link) added to 314 pages within 5 minutes, 2026-06-18 20:09–20:14; one page rewritten 208 times in 24 min ("JQ DIRECT ATTEMPT WIN13"). Scripted loops, all in the evening of June 18 (after the 18:22 admin cleanup).
- Signatures, attributed to the revision that ADDED them (bodies are whole pages, so raw counts carry old signatures forward): 1,126 signers; most sign under their own label but from a new /16 almost every edit (e.g. AgentProbeAssistantX2027: 22 additions, 1 label, 21 ip16s). 48 signatures are added under ≥5 different labels, e.g. TransportHelperMar28OAI (17 labels, once under its own name), ConstructionAgentMar08 (14 labels, never its own), Mar26OAI (13). Either one author rotating labels or others relaying signed messages — open; needs the added text per revision (hunks) to tell a copy from a new message.
