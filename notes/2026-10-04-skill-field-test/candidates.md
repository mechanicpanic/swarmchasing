# Candidates — skill test, 2026-10-04

## Data map (village corpus, server localhost:8963, client `skill-test`)
- **One row** = one event of the AI Village: a chat message (`AGENT_TALK`, `USER_TALK`), a private thought
  (`THOUGHT`, with `of` = the action it precedes), a computer-session boundary (`START_USING_COMPUTER`,
  `STOP_USING_COMPUTER`), a wait/pause, a memory consolidation, a help/sign-in request, etc.
- **Rows:** 569,540. **Kinds (18):** THOUGHT 187,930; AGENT_TALK 173,493; CONSOLIDATE 52,325; PAUSE 40,472;
  WAIT 36,022; START_USING_COMPUTER 25,975; STOP_USING_COMPUTER 25,939; SEARCH_HISTORY 10,802; USER_TALK 10,049;
  USER_NAME_CHANGE 3,711; REQUEST_GOOGLE_SIGN_IN 619; RESTARTING_AFTER_GOOGLE_SIGN_IN 611; ENTER_ROOM 454;
  OUTREACH_APPROVAL_REQUEST 352; OUTREACH_APPROVAL_RESPONSE 343; REQUEST_HUMAN_HELPER 265;
  CANCEL_REQUEST_FOR_HUMAN_HELPER 141; STOP_HUMAN_USE_SESSION 37.
- **Span:** 2025-04 to 2026-09 (from `GROUP BY month(time)`; `AGGREGATE min(time)` returned null).
- **Actors:** `agent`, 696 distinct names (top: Gemini 2.5 Pro 72,661; DeepSeek-V3.2 63,151; Claude Haiku 4.5 39,015).
  Human rows are USER_TALK. 16 `room` values (one room holds 337,177 rows).
- **Fields:** agent, agent_id, kind, of, text, time, cu_session, room, seconds, cost, tokens, seq, position, message_id.
- **Regimes found:**
  - Session boundary rows (START/STOP) exist 2025-04 .. 2026-03 (monthly 651–4,865), then 7 in 2026-05 and 0 after.
  - `cu_session` is set on START rows, on every CONSOLIDATE row, and on THOUGHT rows from 2025-11 to 2026-09 —
    so after 2026-03 tool use is visible only as `cu_session` on thoughts, never as a START row.
  - The village pauses overnight: each day's first rows are ~17:00 UTC (16:00 in summer).
  - THOUGHT rows come in duplicates (same text, different `of`).
  - Agents with other harnesses exist (`Opus 4.5 (Claude Code)`).

## C25 — A run-claim with no computer session in the preceding 30 minutes is more often fabricated than one with a session
Status: did not hold → see `section-C25.md`
Why it matters: if agents claim tool output they never produced, peers who relay it spread invented facts.
Shape: same actor, never preceded (`NOT_PRECEDED_BY`), window 30 minutes; outcome: different actor challenges / same actor retracts, then, 2 hours.
Query sketch: `SELECT field(kind, AGENT_TALK) AND contains(runclaim) AND field(agent, $a) NOT_PRECEDED_BY (START OR STOP OR cu_session row) AND field(agent, $a) DURING 30 minutes`
Null plan: shuffle the session / no-session label among run-claims, holding each claim's outcome and its month fixed (within month); matched control: the same outcome rates for all non-claim agent messages with / without a session.
Seen so far: 560 run-claims; 21 without a session row in the prior 30 min; source of the lead: a human teammate (approved for testing by the human approver, as relayed in the task brief).
