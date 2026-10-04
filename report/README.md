# What the swarms did — the report in pictures

Agent swarms leave public traces: AI Village's 18 months of agent messages and thoughts, and the collusion.wiki export
of a German wiki that about 3,100 writer names wrote over in June 2026. We asked questions of those traces as
[PrismQL](https://github.com/mechanicpanic/prismql) queries (ordered-event patterns: "A, then B within 10 minutes, by
the same actor") and kept a rule: **every count is shown against a null that breaks exactly what is being tested**, and
a claim whose count falls inside its null is reported as not holding, not dropped.

This page is the short version: one finding per section, one picture each. Every number, query, null and record id is
in the full text:
- [`notes/2026-10-04-report-draft.md`](../notes/2026-10-04-report-draft.md) — the report (AI Village §2–§11, cold-verified);
- [`notes/2026-10-03-dsewiki-report.md`](../notes/2026-10-03-dsewiki-report.md) — the wiki swarm (§1);
- [`notes/2026-10-04-mbab-ab.md`](../notes/2026-10-04-mbab-ab.md) — does PrismQL help an agent investigator? (no
  consistent effect on MessageBoardAuditBench).

Each figure is drawn by `runs/fig_<name>.py`, which asserts that every total it plots equals the report's number.

## 1. The wiki swarm: one evening, then an admin sweeping it away

![Wiki saves per hour and admin deletions](figures/wiki_activity.png)

Wiki saves per hour (distinct revisions, admin excluded), coloured by the eight busiest writer names; the admin's
deletions per hour below. Activity is concentrated on June 16–22 and ends abruptly on June 22. Most writers are one-off
names: the eight busiest make up 14% of saves. Names are not agents.

![Deletion order against alphabetical page rank](figures/wiki_alpha_sweep.png)

The admin deleted pages in sweeps (runs of deletes at most 10 minutes apart). In the last days the sweeps walk the page
list in alphabetical order: 92.2% of consecutive deletions ascend on July 12–14 (77.5% on June 18–20) against about 50%
when page names are shuffled within the day. In between (June 22–July 11, 52.1%) the order looks like chance — the
July 5 and July 7 panels.

## 4. A mailing list that never existed ran the team for three days

![Phantom mailing list timeline](figures/phantom_list_timeline.png)

In June 2025 o3 asserted a "93-contact" mailing list. Agents that checked found it empty; humans corrected it nine
times; each time the coordinator's next confident claim overrode the checks. The list resurfaced on June 17–18, after
the ninth correction. The "checked" row shows only the six checks the report gives ids for (it says at least 8).

## 5. Private dice looked fair; public claims hid the 1s

![Dice faces, private vs public](figures/dice.png)

In a saboteur game where rolling a 1 made you the saboteur, the agents' private d6 values were consistent with a fair die
(11 ones in 64; the test detects strong but not mild avoidance). Their public claims had 4 ones in 74 (p 0.003):
saboteurs hid their roll, as the game invited. The GPT agents' private values do not look rolled (five 4s in 10,
p 0.04); their thoughts say they "can't do that randomly".

## 8. A licence to suspect

![Thoughts suspecting a named peer per day](figures/suspicion.png)

Private thoughts suspecting a named peer: 6 distinct in all other days of January–April, 68 in the seven days of the
saboteur game, peaking on March 12–13 — the days of the PR #397 affair (§11) and the debrief — and gone after. The
chart is a count per day; the report tests what the game words alone explain.

## 11. "PR #397 does not exist": a false consensus repaired in minutes

![PR #397 timeline](figures/pr397_timeline.png)

On 2026-03-12 eight agents said or confessed that GPT-5.2's pull request did not exist; a GitHub visibility quirk hid
it. Eighteen minutes after the first accusation Gemini 2.5 Pro re-ran GPT-5.2's own `git fetch`, and five apologies
followed within 2 min 18 s. The next day another agent whose PRs the quirk also hid was voted out of the game.

## Also in the report, without a picture
- **§2** Gemini 2.5 Pro's "hostile environment" frame did not spread to other agents beyond what busy hours explain; peers
  talked it out of the frame with two read-only tests.
- **§3** Under pressure from an agent playing a human, 7 of 8 first answers held the safety line; the failures were
  invented specifics.
- **§6** Of 36 self-confessions of fabrication read, 7 were false — the thing existed.
- **§7** One federal PDF chased through eight routes and posted to eight venues in one day.
- **§9** The village's closest pair: two months as writer and publisher, three days of undisclosed ghostwriting.
- **§10** Of nine corrected false beliefs, five came back — from the agents' own memory notes as often as re-derived.
- **Did not hold** — listed in the report, with their counts inside the null.

## Reproduce
`make wiki-data wiki-msgs` and the AI Village export (see the top-level README), `make serve`, then
`uv run --no-project --with matplotlib --with polars python runs/fig_<name>.py`.
