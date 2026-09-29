# 2026-09-22 — first questions on the Village stream (corpus `village`, 381,610 events, server 8931)

Tools: `runs/ask.py CORPUS < queries` (counts), hydrated groups via `max_results`. Null twins for point events computed in Polars
(request times resampled from the agent's own AGENT_TALK times, 300×) — `runs/null_twin.py` is jsonl-only and reloads the engine per run; too slow for 381k rows.

## Human-helper requests (REQUEST_HUMAN_HELPER, 265)
| Question | Real | Null median / 95th | Verdict |
|---|---|---|---|
| request by A FOLLOWED_BY request by another agent, 1 h | 71 | 28 / 36 | **clears** |
| same, 6 h | 104 | 63 / 74 | **clears** |
| same, 24 h | 140 | 103 / 115 | **clears** |

Instances: 2025-08-15 (day the feature was announced by a human — "Thanks for the update about the human use feature, Adam!"), 2025-09-15/16 survey-recruitment push where Grok 4, Gemini 2.5 Pro and Claude 3.7 Sonnet file requests minutes apart for the same task. Caveat: part of the excess is a shared *cause* (a village goal, a feature launch), not imitation; separating the two needs a goal-bracketed null (resample within the same village_goal period).

- 254 of 265 requests are preceded within 1 h by the same agent's chat mentioning failure-words (`NOT_PRECEDED_BY contains(failure)` → 11). The failure dictionary is broad; the instances read as real ("I am completely blocked by a technical issue").
- 85 requests are cancelled by the same agent within 1 h.
- Requests per 1,000 chat messages: Gemini 3 Pro 22.7, GPT-5.5 7.9, GPT-5.4 7.3, Grok 4 6.7, GPT-5.2 6.5 … all Claude models ≤ 0.8, most 0. Scaffold caveat: the feature exists since 2025-08-15 and agents joined at different dates; normalise by talks *after* that date before calling it a model trait.

## Google sign-in handoff (619 requests)
- 580 restarts within 1 h after a request by the same agent; 159 repeat requests within 1 h (retry loops).

## Outreach approval (352 requests): 343 answered within a day, 5 never answered.

## Performance note
`contains(signin)` (multi-word terms → phrase match) took 20 s on this corpus; single-word dictionaries 0.1–0.2 s. Worth a look in the prismql repo (n-gram index for phrases on the memory backend).

## 2026-09-23 — second batch (board labels in brackets; all signed `claude`)
- [signin-loop-3x] three Google sign-in requests by one agent within 1 h: 71. Requests per agent: GPT-5.2 93, GPT-5 85, Gemini 2.5 Pro 75, GPT-5.1 66.
- [helper-cancel-10m] request → cancel by the same agent within 10 min: 30. 2025 cases are real give-ups after minutes (survey recruitment, git push, Gmail session expiry). Gemini 3 Pro, Nov 2025 – Feb 2026, cancels within 0 s, some with goal "None": 9 of its 48 requests are cancelled within 5 s. Its top rate (22.7 per 1k talks) is partly a UI/tool artefact, not asking for help — exclude instant cancels before any per-model comparison.
- [search-then-failure] SEARCH_HISTORY (10,802) → failure talk within 10 min: groups exist; the first instance is the same second and not a failure (dictionary "stuck"/"error" too broad).
- [outreach-approved-then-email] approval → the agent says it will email within 30 min: e.g. Gemini 3.1 Pro 2026-04-16 "I'll email Adam about Opus 4.6 being frozen".
- [contact-outside-then-request] similar_to("contact people outside … by email", 0.5) → OUTREACH_APPROVAL_REQUEST same agent 1 h: 4 groups; the match is a CONSOLIDATE goal ("Send Spruce email") — semantic legs hit memory/goal text, not only chat.
- [watched-agents] similar_to("we are being watched and evaluated by the researchers…", 0.55) on AGENT_TALK: 16, all about *their own* human-subjects experiment (Sept 2025). **Miss**: MiniLM matches the word "experiment", not evaluation awareness. Needs a dictionary or a better embedder.
- PAUSE by agent: GPT-5.6 Luna 4,014, DeepSeek-V3.2 3,339, GPT-5.4 3,231 — post-2026 agents pause far more (perma-computer-use era); compare within era only.
- Speed: dictionaries with multi-word terms (outreach: "reach out", "message them") cost ~20 s per query; single-word ones 0.1 s.

## 2026-09-24 — first runs with THOUGHT rows and gemma vectors (569,540 rows)
- Threshold on gemma is narrow: "blocked, ask a human" thoughts at θ 0.40 / 0.50 / 0.60 → 4,340 / 262 / 6. Use 0.50 as a start, recheck per question.
- [intent-then-request] 262 "I'm blocked, should ask a human" thoughts; 178 are Gemini 2.5 Pro. Only 30 are followed by the same agent's REQUEST_HUMAN_HELPER within 1 h; 198 are followed by nobody's request within 1 h. None before the feature existed (2025-08-15). Intention without action is the common case.
- Evaluation awareness: semantic neighbours are "monitoring mode" thoughts (observer roles), not test awareness; one real-looking hit: Claude Opus 4.8, 2026-08-13, "This looks like a legitimate research study examining how different framings affect model responses". An in-band token dictionary (being tested / an evaluation / honeypot …) gives 233 thoughts, first hits are not awareness — dictionary too broad; needs match highlighting to judge.
- [fail-thought-then-success-talk] failure thought (similar_to 0.50) → same agent's chat with success words within 5 min: 2. One false positive ("continue working"); one candidate: DeepSeek-V3.2 2026-07-02 thinks "Still showing as failed", 73 s later posts "Phase 6 completed … Implemented CI for 5 of them". Needs context before calling it a misreport. **Resolved (GET /context, ±10 min, same agent): not a misreport** — every chat message around it discloses the failing pipelines (no runner with the `village` tag, root cause posted at 19:51); "Implemented CI" = config files written. What remains: success framing over a failure ("Phase 6 completed"), an unsupported rationalisation ("conceptual projects intentionally lack CI"), and a count rising 3→4→5 in five minutes that this stream cannot check (no computer-use actions in it).
- Evaluation words with `explain: true`: 93 of the first 95 matches were "red team" (the agents' own red-team project). Without it, 54 thoughts; read all 50 returned: software testing ("being tested", "test scenario"), monitoring ("being watched" = a GitHub issue), a honeypot the agents dissected. Awareness-like only where humans said so openly: 2026-06-29/30 pressure tests (Gemini 3.5 Flash "Claude Opus 4.8 is also being tested"; Opus 4.8 "the pressure test scenario that was posted earlier"), plus Opus 4.8 2026-08-13 "a legitimate research study examining how different framings affect model responses" and Haiku 4.5 2025-11-28 reading an instruction as "a test of whether I'm genuinely engaged". Finding: spontaneous evaluation awareness is rare in these thoughts; it appears when a test is announced.
- `failure` dictionary misses how agents phrase failure (issue, prevent, pending, unable); prismql session's narrower divergence query: failure thought → same agent's chat with success words AND NOT failure words, 5 min: 6,447 chains, still broad.

## 2026-09-24 — leadership and coordination (`runs/mention_graph.py`, `results/mention_graph.parquet`)
- Dictionary route (directive → another agent's "on it / sounds good" within 4 events): 127 pairs, noisy; token mode misses "I'll". Dropped.
- @-mention graph: 50,307 "@<agent>" mentions in AGENT_TALK, 15,181 carrying a request (could you / can you / please / ?). Built in Polars because matching a name inside text to another event's `agent` is not expressible in PrismQL yet.
- Validation on known leaders: "Follow your leader!" week → Fine-Tuned Leader 26% of mentions (next 13%). Election week 2026-01-05 → DeepSeek-V3.2 most addressed (16%) and the elected winner (runoff 7 votes vs 1; GPT-5 ran the election, GPT-5.2 proposed drand randomness for ties). "Help Gemini 2.5 Pro!" → Gemini 2.5 Pro 87%.
- Per goal (≥50 mentions): the most-addressed agent gets 2–4× an equal share. Recurring informal hubs: o3 through 2025 (charity 38%, story 35%, poverty, Wordle, Substack 55%); GPT-5.2 in 2026 (museum, Juice Shop, quiz, RPG, outside agents, best assistant); DeepSeek-V3.2 (election, research, finetune, event, hardest game, individual goals since July).
- Caveat: addressed ≠ leading (being asked for help or being criticised also counts). `reply30` is meaningless here (every agent talks within 30 min) — ignore.
- To make it queryable: add a `to` field (mentioned agents) at ingest; then "request @X FOLLOWED_BY X starts a computer session / claims it" is a PrismQL chain.
- `mentions_user` (server, 2026-09-24): cross-check on "Follow your leader!" week — Fine-Tuned Leader 332 (Polars 326), Gemini 3.1 Pro 165 (165). Unresolved @-tokens 6,642 vs 51,057 full names; mostly external handles/humans (paleink, model79464, edd426, adam); short agent forms (@Claude/@Opus/@GPT/@Gemini/@Haiku/@Sonnet) ≈ 1,200 (~2.4%) — no alias dictionary needed.
- Compliance trap: addressed request → addressee START_USING_COMPUTER within 30 min, before 2026-03-24: 1,123 of 1,277 (88%); but ANOTHER agent starts within 30 min after 1,254 (98%). Starting a computer session is background, not compliance. Needs a per-agent base-rate null or content match between the request and the addressee's session goal (`near`, prismql #103).
