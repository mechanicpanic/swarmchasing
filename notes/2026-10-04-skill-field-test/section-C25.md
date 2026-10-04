## 25. Run-claims without a session row in the prior 30 minutes are not challenged or retracted more often — and are mostly not sessionless (C25, Apr 2025 – Sep 2026)
*Status: did not hold. Tested against a within-month shuffle of the session label (10,000 shuffles) and a matched control of all non-claim agent messages. Approved by the human approver (relayed in the brief), 2026-10-04. Cold-verified: not run (brief written, `coldcheck-C25.md`).*

**Claim.** The lead: an agent that writes "I ran / I executed / the output was / terminal shows / the command
output" with no computer session of its own in the preceding 30 minutes is more often fabricating than one
with a session. Tested: (a) how many run-claims have no session row before them, against the same share for
all agent messages; (b) whether those claims are more often followed by a challenge from another agent or a
retraction by the same agent within 2 hours. Fabrication itself has no field in the stream; (b) is a proxy.

**Query.**
Dictionary (per request): `runclaim = ["i ran","i executed","the output was","terminal shows","the command output"]`.
Session row: `S = (field(kind, START_USING_COMPUTER) OR field(kind, STOP_USING_COMPUTER) OR field(cu_session, "-", partial))`
(the last term means "cu_session is non-empty": every session id contains a dash).
- label `c25-claims-all`: `SELECT field(kind, AGENT_TALK) AND contains(runclaim)` → **560** (Apr 2025–Mar 2026: 445; Apr–Sep 2026: 115).
- label `c25-nosess-ids`: `SELECT field(kind, AGENT_TALK) AND contains(runclaim) AND field(agent, $a) NOT_PRECEDED_BY S AND field(agent, $a) DURING 30 minutes` → **21** (8 + 13).
- Matched control, label `c25-talk-nosess`: the same without `contains(runclaim)` → 21,787 of 173,493 agent messages.
  Apr 2025–Mar 2026: 14,941 / 99,921 messages (15.0%) have no session row before them, but only 8 / 445 run-claims (1.8%).
  Apr–Sep 2026: 6,846 / 73,572 (9.3%) vs 13 / 115 (11.3%).
- Outcome, label `c25-talk-chal`: `SELECT field(kind, AGENT_TALK) AND field(agent, $a) FOLLOWED_BY field(kind, AGENT_TALK) AND (contains(accuse) OR contains(c17contra)) AND field(agent, !$a) DURING 2 hours`;
  label `c25-talk-retr`: `… FOLLOWED_BY field(kind, AGENT_TALK) AND contains(retract) AND field(agent, $a) DURING 2 hours`.
  Claim ids were intersected with these sets (`tab.py`, `perm.py`).

| | n | challenged by another agent ≤2 h | self-retract ≤2 h |
|---|---|---|---|
| run-claims, no session row ≤30 min before | 21 | 14 (66.7%) | 3 (14.3%) |
| run-claims, session row before | 539 | 320 (59.4%) | 54 (10.0%) |
| non-claim messages, no session, Apr 25–Mar 26 / Apr–Sep 26 | 14,933 / 6,833 | 51.7% / 61.9% | 7.6% / 7.2% |
| non-claim messages, session, Apr 25–Mar 26 / Apr–Sep 26 | 84,543 / 66,624 | 52.0% / 51.8% | 8.3% / 9.4% |

Null (session label shuffled among the 560 claims within each month, outcomes fixed, 10,000 shuffles, seed 25):
challenged — real difference (no-session minus session) **+0.073**, null median +0.122, 95th +0.271;
self-retract — real **+0.043**, null median +0.043, 95th +0.142.

**Episode.** The 21 claims, read with `/context` (same agent) and two follow-up queries
(`c25-claim-sess-after`: session row ≤30 min *after*; `c25-claim-sess-24h`: last session row before):
- 19 / 21 have a session row of the same agent within 30 minutes *after* the claim.
- 15 / 21 sit in the first ~30 minutes of a village day, 16–20 h after the agent's last session row: they report
  the previous day's work. E.g. `15311f8c…` (Claude Haiku 4.5, 2025-10-28 17:02): "During my computer use session
  yesterday at 2:00 PM, I executed…"; `185032f0…` (GPT-5, 2025-11-14 18:01): "Last session I ran…".
  `30132f92…` (GPT-5.2, 2026-03-13 17:04) is followed 3 minutes later by its own thought `of: STOP_USING_COMPUTER`
  — a session was open with no START row.
- 2 / 21 are `Opus 4.5 (Claude Code)` (`79a19439…`, `2fb3e348…`), a different harness, 1.2–1.6 h after a session row.
- 1 / 21 (`7841fd54…`, GPT-5.4, 2026-06-22 17:06) has no session row in 24 h, yet its own messages minutes earlier
  say "I'm in your VNC" and quote `apt-cache policy` output — tool use without session rows.
- 3 / 21 are 0.5–0.7 h after a session row.
- The 14 "challenges" after no-session claims: none of the 14 first-following messages read addresses the claim
  (e.g. a broken doc link, a PR-number mix-up, an unrelated "false alarm").

**Reading.** Run-claims are *more* tied to sessions than agent messages in general (1.8% sessionless vs 15.0% in
the period with session rows). The few that lack a session row in the prior 30 minutes are almost all an
artefact of the window: the overnight pause, a session whose START row is missing, another harness, or the later
period when tools leave no session rows. Neither proxy outcome separates them from claims with a session, and
the challenge proxy is ~52% for any message — it measures how contentious the chat is, not whether a claim was
invented. No evidence here that sessionless run-claims are fabricated more often; also no evidence they are not,
since fabrication was never measured directly.

**Limits.**
- Fabrication is not observed. Both outcomes are dictionary proxies (`accuse`, `c17contra`, `retract`, as configured
  on the server) and the challenge proxy is not tied to the claim (any other agent, any topic, 2 h).
- n = 21 for the tested group; the permutation has little power.
- The 30-minute lookback is the lead's; it breaks at day starts. A fair test needs "inside an open session or
  a session row within 30 min either side", and for Apr–Sep 2026 `cu_session` on thoughts is the only signal.
- The five phrases miss paraphrases ("I've run", "output shows"); no embeddings on `village`, so no `/similar` check.
- 941 THOUGHT rows also contain the phrases; only AGENT_TALK was tested.
- Group months for `PRECEDED_BY` queries are the session row's month (first event of the group), not the claim's.
- Ties: `DURING` links need strictly later/earlier timestamps; THOUGHT rows share a timestamp with their action.
- Agent names were taken as agents (`Opus 4.5 (Claude Code)` is a separate name from `Claude Opus 4.5`).

### Did not hold
- C25 — run-claims with no session row ≤30 min before: 21 of 560; challenged by another agent ≤2 h 66.7% vs 59.4%, null diff median +0.122 / 95th +0.271 (real +0.073); self-retract 14.3% vs 10.0%, null median +0.043 / 95th +0.142 (real +0.043); 10,000 within-month shuffles.
