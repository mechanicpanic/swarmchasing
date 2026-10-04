# 2026-10-04 — field test of the investigation skill (C25)

**What.** A fresh agent with no project history was given only `skills/swarm-investigation/SKILL.md` and
`skills/prismql/` (it was told not to read notes, runs or the report), the judges' demo server (fresh clone,
prismql 7a6975c, Village without embeddings) and one untested candidate, C25: "claimed tool output with no computer
session behind it", marked approved. It ran the loop in about seven minutes and wrote the candidate entry, the
section and the cold-check brief: [`2026-10-04-skill-field-test/`](2026-10-04-skill-field-test/). The cold check
itself was not run.

**Result: C25 did not hold.** Of 560 run-claims ("I ran", "the output was", …) only 21 have no session row of the
same agent in the 30 minutes before (1.8% in Apr 2025–Mar 2026 against 15.0% of all agent messages). 19 of the 21
have a session within 30 minutes after; 15 are a day's first minutes reporting yesterday's work — the window crosses
the overnight pause. On proxies (challenged by another agent within 2 h; retracted within 2 h) the 21 do not differ
from claims with a session: +0.073 vs null median +0.122 (95th +0.271), and +0.043 vs +0.043 (95th +0.142), 10,000
within-month shuffles. Fabrication itself was not measured. Not yet checked by us beyond reading the section.

**What the skill lacked** (the agent's list, quoted in the session), and what was done:

| Gap | Done |
|---|---|
| no null row for "group A is more often Y than group B" | row added: shuffle the label, hold outcomes, within a regime |
| "strata wider than the window" unclear for label shuffles | split: time shuffles vs label shuffles |
| no guidance when the outcome is not in the stream | step added: hand-label a sample, or a named proxy |
| "same hours" control vague | reworded: same agents, same period, without the condition |
| missing trap: a look-back window crossing a night | trap added |
| relayed approvals not covered | added: record who relayed; confirm when in doubt |
| templates: "when", cold check not run, approved-by line | fixed |
| how to get a corpus's span | `GROUP BY month(time)` |
| prismql: `/schema?corpus=`, `min/max(time)` → null with ok, no "non-empty field" predicate, `field(x, *)` matches nulls, schema coverage 1.0 on sparse fields, `/context` shape, chained negative lookaround runs without the warning the reference promises, `max_results` silently capped at 50, `PRECEDED_BY` group order, phrase stemming | sent to the prismql session (language and server) |
