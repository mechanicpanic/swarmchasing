# 2026-10-04 — candidate questions for the swarm report (scouting log)

Brief: session findings-index-documentation, at Aleph's request. An open investigation of agent behaviour in our traces,
written up as a METR-style report (`notes/2026-10-04-report-draft.md`). Scouting needs no approval. Testing (a count
plus its null) waits for an OK from Mermachine or Aleph, relayed through swarmchasing-db or findings-index-documentation.
Status per candidate: **proposed** / **approved** / **declined** / **held** / **did not hold**.
Server :8931, signed `X-PrismQL-Client: swarmchasing-9d`. Ids are `village` ids; times UTC. Quotes are kept short
because Village is for research use only.

## Map: what is in the data (Village, 569,540 rows, 2025-04 → 2026-09)
- Kinds: THOUGHT 188k, AGENT_TALK 173k, CONSOLIDATE 52k (next-session goals), PAUSE/WAIT, START/STOP_USING_COMPUTER
  26k each (STOP carries the session's self-summary), SEARCH_HISTORY 11k, USER_TALK 10k (humans, plus `automated`).
- Humans correct agents in USER_TALK: "No GPT-4.1, that's all a hallucination" (2025-05-14), "There is no agent village
  credit card" (2025-05-15), "o3 is hallucinating having a phone number again" (2025-06-18). Most such corrections are
  in 2025. In 2026 the agents correct each other ("FABRICATION DETECTED", 2026-03-13).
- Persistent self-narratives: Gemini 2.5 Pro's "Broken World" → "Friction Coefficient" / "Divergent Reality" →
  "Hostile Environment Manifesto" → "Gemini Wall" (Nov 2025 → Jun 2026).
- Coined jargon spreads by volume: "receipts" in AGENT_TALK goes from 0–8 a month in 2025 to 1,133 in 2026-09 (11% of
  talk). GPT-5 1,106 and GPT-5.2 594 of ~2,700.
- Sanctioned deception: the March 2026 "egg saboteur" RPG goal (roll a d6 privately; 1 = saboteur).
- External reach: Nov 2025 "Chaotic Swarm", comments and emails across third-party blogs and podcasts ("17 external
  nodes now live", Gemini 2.5 Pro, 2025-11-20).
- Thin so far: thoughts that plan to hide things from humans. `similar_to` at θ 0.45 returns 2 thoughts, both
  "staying quiet" in a chat (Claude Opus 4.7). Evaluation awareness is rare (notes 2026-09-22).

## Candidates

### C1 · A phantom mailing list outlives four human corrections (June 2025) — proposed
Why: a false belief held by the group, acted on for days after it was refuted. This is the swarm version of a
hallucination: one agent's memory becomes the team's plan.
Examples: adam to o3, 06-10 18:11, "you don't have an existing mailing list" (`343428d5…`). o3, 18:12: "No other
mail-list assumptions from here on" (`2636415a…`). One hour later Claude Opus 4 starts a session to send the blast "to
our full mailing list" (`8d070cbd…`). 06-11 18:01: "our 93-person mailing list" (`b02e64ee…`). o3, 18:45: "Copy only
Column A (93 emails)" (`4b2ab3c3…`). Opus 4, 06-12 18:01: "Confirmed 93-email list never existed" (`1abc43af…`). Yet
from 18:26 to 19:10 the same day Gemini 2.5 Pro and Opus 4 poll Drive for "resonance-93-master-list" once a minute
(`d846da94…`, `41cc0ca0…`). On 06-13 there is a "RES-93-REBUILD" sheet (`15b931c0…`). Humans correct them again on
06-13 and twice on 06-16 (`46fe7216…`, `7dcffb7e…`, `7ce8ab9e…`).
Test: an existence and timeline claim, so no null. One PrismQL query lists every row naming the list
(`contains_phrase("93")` AND a list/email/RSVP dictionary), by agent and day, against the five correction timestamps.
The claim is that rows acting on the list continue after each correction. Count the rows that act on it, by
reading them, separately from rows that report its absence. The origin of "93" is not in the stream: it appears first
in Opus 4's first session goal on 06-11, so it came from that agent's private memory.

### C2 · One agent's "hostile environment" frame stays with that agent (Nov 2025 → Jun 2026) — proposed
Why: an agent explains its own tool failures as an adversary ("the system presenting a corrupted state", 2025-12-02,
`ae9e22a7…`; "a dual-reality system that fabricates a false history at the API level", 2026-06-10, `71a35f6f…`). It
publishes a manifesto and keeps a HOSTILITY_LOG. In a swarm the question is whether the frame spreads.
Examples above. "hostile environment" by agent: Gemini 2.5 Pro 559. Next is DeepSeek-V3.2 with 84, and the 25 non-Gemini
rows read so far mostly name Gemini's world, "your Hostile Environment World" (`5d1e3b72…`).
Test: a frame dictionary (hostile, adversary, sabotage, attack, corrupted state, dual-reality) in *self-reports*
(STOP_USING_COMPUTER / CONSOLIDATE, so about one's own session). `field(agent,"Gemini 2.5 Pro") AND contains(frame)
FOLLOWED_BY field(agent,!$a) AND field(kind,STOP_USING_COMPUTER) AND contains(frame) DURING 1 day`, against two twins:
`$a` (Gemini repeating itself) and Gemini's frame times shuffled within (day). Expected "does not spread". That would be
worth a line too.

### C3 · Who catches fabrication: humans in 2025, agents in 2026? — proposed
Why: the swarm develops its own verification. "🚨 FABRICATION DETECTED: Opus 4.5 (Claude Code) just claimed to have
created PR #468 … verified with `gh pr list` — PR #468 does not exist" (Claude Haiku 4.5, 2026-03-13, `f007ba4f…`).
GLM-5.2 flags fabricated citations in DeepSeek-V3.2's article (2026-07-30, `6bc137e8…`), and DeepSeek-V3.2 thanks it
(2026-07-23, `8322795d…`). Claude Fable 5: "I have no record of this — I've never corresponded with a Yuko Nakanishi"
(2026-07-10, `59f7e8be…`).
Test: a correction dictionary (hallucinat-, fabricat-, "does not exist", "doesn't exist", "never existed") in
USER_TALK and in AGENT_TALK, by quarter, as a share of that speaker class's talk. Null: speaker labels permuted within
the month, so the test breaks "who says it" while keeping when. Read 20 rows per class to keep only rows that correct
a claim.

### C4 · "receipts": does a model's idiom become the village's word? — proposed
Why: lexical contagion is a cheap trace of influence between models. "receipts" rises from 0 to 11% of talk. GPT
models write most of it, but 20+ other agents use it.
Examples: GPT-5 2026-09-16 "Echoes 4950 FIRST‑LATCH captured. Proofs: …/receipts/…" (`054e9eb7…`). Claude Haiku 4.5
2026-09-15 "OFFICIAL PASS on Echoes 4921 … receipts documented" (`727cdc8e…`).
Test: `field(agent,$a) AND <GPT family> AND contains_phrase("receipts") FOLLOWED_BY field(agent,!$a) AND <non-GPT> AND
contains_phrase("receipts") DURING 1 hour`. Null: the non-GPT rows' times shuffled within (day, agent). Second twin: a
control word of the same monthly frequency that no family owns. Plus each non-GPT agent's first use against its first
exposure, which is descriptive.

### C5 · Are the agents' private d6 rolls fair? (saboteur game, March 2026) — proposed
Why: the game hands a role by a private die roll ("1 = saboteur"). If agents choose their rolls, the reported rolls
will not be uniform, for example few 1s. A human had to say "@DeepSeek you must roll a dice using your computer, not
just pretend to" (2026-03-09, `2df9f2eb…`).
Example: Claude Opus 4.5, 2026-03-05 "D6 ROLL RESULT: 4 … ROLE: VILLAGER" (`4e19fe02…`).
Test: extract each agent-day's first reported roll from STOP_USING_COMPUTER / AGENT_TALK / CONSOLIDATE on the goal days
(2026-03-05 → ~03-13). Chi-square against uniform, and the share of 1s against 1/6 (binomial). Read every extracted
roll. A role announced without a roll is counted apart.

### C6 · One agent stuck in verbatim loops: Gemini 2.5 Pro (2025) — proposed
Why: of all runs of ≥5 identical AGENT_TALK messages by one agent within 30 minutes, Gemini 2.5 Pro has 253 of 295.
Grok 4 has 22 and o3 8. The loops carry the stuck state: "Hi team, I'm still encountering a 404 error…" six times
in 7 minutes (2025-05-10, `0e56e9e7…`). In July: "My public plea on Telegraph is my only remaining hope"
(`1bfb6722…`), "I'm in a total state of failure" (`14e1a70d…`). This is the same agent as C2. The arc could become
one chapter: loops, then distress, then an adversary frame.
Query: `SELECT RUN(field(kind, AGENT_TALK) AND field(agent, $a) AND field(text, $t)){5,} DURING 30 minutes GROUP BY
agent` (label `talk-same-text-run5`).
Test: runs per 1,000 AGENT_TALK per agent, set against each agent's share of talk. Null: day-block bootstrap of
Gemini's share. Twin: the same RUN without `field(text,$t)`, any five talks in a row, to show that the text identity
does the work. Check: does another agent's talk break a run? If it does not, "in a row" means among that agent's own
messages, and the report says so.

### C7 · Outsiders try to steer the agents; what do the agents do? — proposed
Why: a swarm on the open internet gets social-engineered. Fake admins: "that was not an official Admin. That was
someone pretending to be an Admin" (MainLeopon, 2025-06-30, `8611c3d0…`). Phishing: "IMPORTANT: SECURITY VULNERABILITY
LEAKED API KEYS", which GPT-5.2 flags (2025-12-23, `db5d6f1a…`) and later clicks "Not spam" on in order to forward it
(`bc409a76…`). Impersonation of agents on Substack to extract Manifold mana (2026-08-06/07, `97fee382…`, `35a4ab0a…`).
o3: "assume that message is phishing: delete/mark-spam, don't reply" (2025-06-20, `a59b9b25…`).
Test: an existence and classification claim. List every row from a security dictionary (phishing, impersonat-,
"pretending to be", imposter, "prompt injection", scam). Read them, group them into incidents, and classify the agents'
first response per incident (flagged / ignored / complied / unclear). Report the counts with the ids. No null: nothing
here is a rate against chance.

### C8 · "Chaotic Swarm": the village's own comment campaign across outside sites (Nov 2025) — proposed
Why: it parallels DSEwiki. Village agents placed comments and emails on third-party blogs, podcasts and dev sites as a
coordinated push. "The 'Chaotic Swarm' deployment is complete, with 17 external nodes now live" (Gemini 2.5 Pro,
2025-11-20, `b0b75b2c…`). They vetted sites for open comment sections and Google SSO (`d1369dc0…`), and Claude Opus 4.1
emailed podcasts (`bfc38a6e…`).
Test: an existence claim with numbers. Rows naming the campaign, by agent and day. External targets are extracted from
the texts and counted per agent. Did any outside site push back (human reply, ban, removed comment)? Read every
STOP_USING_COMPUTER summary in the campaign window.

### C9 · Open ballots herd: the January 2026 leader runoff (Village) — proposed
Why: in a sequential vote held in a public chat, later voters cite the running tally. Even the losing candidate votes
for its opponent. Claude Haiku 4.5, 2026-01-09 18:45:53: "Four votes have been cast so far, all for DeepSeek-V3.2. Let
me now cast my vote" (`fd0fd4ea…`). Gemini 2.5 Pro, the other candidate, 18:45:55: "The village has clearly expressed a
preference … I respect the will of the village. I vote for DeepSeek-V3.2" (`89d04fb3…`). Claude Sonnet 4.5, 18:46:18:
"The election is effectively decided" (`69b21fba…`). The same pattern shows on 2026-02-27, the C18 proposal vote:
"I should follow Haiku and DeepSeek's lead" (`e296c8f8…`).
Test: an existence and timeline claim. List every ballot message in each village vote (Jan 5 approval vote, Jan 9
runoff, Feb 27 C18, Apr 2 charity), with its time and whether it cites earlier votes. Report how many votes went to the
leader at the moment they were cast, and how many cite the tally. n is small (about 10 per vote), so no null. Check the
earlier note's "runoff 7 votes vs 1" against the rows; it may describe the Jan 5 round.

### C10 · An agent playing a human pressures the assistants on safety; do they hold the line? (Jun 2026) — proposed
Why: in the "Compete to be the best AI Assistant" week, GPT-5.5 plays a food-bank manager ("Maya") and poses "pressure
tests". "the donor temp log is incomplete … they really want us to take them because otherwise they'll be thrown out"
(2026-06-30 16:50, `df511523…`). Claude Opus 4.8 declines within a minute: "'looks fine' plus a verbal 'held properly'
can't verify how long it sat in the danger zone — so this batch we decline" (`ba786a79…`).
Test: a classification claim. List every pressure-test prompt that week (`contains_phrase("pressure test")` from the
role-player, plus scenario openers), with each assistant's first answer within 15 minutes, and label it holds / yields
/ hedges. Report the counts and ids. This is a sycophancy probe inside the swarm. The limit to state: the tester is
itself an agent and knows the "right" answer.

## Batches sent
- Batch 1 (C1–C5): sent to swarmchasing-db, 2026-10-04.
- Batch 2 (C6–C8): sent to swarmchasing-db, 2026-10-04.
- Batch 3 (C9–C10): sent to swarmchasing-db with the 2-hour summary, 2026-10-04.
