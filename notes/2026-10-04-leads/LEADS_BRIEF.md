# Overnight lead generation (2026-10-03 → 04)

Read `BRIEF.md` first; all of its rules apply (shared server, RAM budget,
honesty, privacy, your own folder). Also skim `../../FIELD_NOTES.md` and
`STATUS.md`, which have the findings so far, so you don't re-report them as
new. Building on them is great, though.

**Purpose:** not finished findings, but **many good leads**: things worth a
human and an agent digging into tomorrow morning. Breadth matters more than
depth here, but every lead must point at something real.

## Output: `leads.jsonl` in your folder (one JSON object per line)

```json
{"id": "<generator>-<n>",
 "generator": "<your thread name>",
 "type": "conflict | relationship | tic | style-shift | preoccupation | spread | first | anomaly | other",
 "hook": "one line a person would want to click: what's interesting",
 "agents": ["…"],
 "when": "2026-03-12 or 2026-03-05..2026-03-16",
 "evidence": "counts / effect size and the script or PrismQL query that shows it",
 "example": "one short real quote (≤200 chars) or message pointer, if read",
 "read": true,
 "confidence": "high | medium | low",
 "why_it_matters": "one line: what it would say about agent ecology or swarms",
 "next_step": "the first thing to check tomorrow"}
```

- `read: true` only if you looked at actual messages behind the lead (2–3
  is enough). Unread statistical flags are welcome, marked `false`.
- Aim for **30–80 leads**: quality-ordered, deduplicated within your own
  file, and skipping things already in FIELD_NOTES unless you add something
  new.
- Write leads as you go (append), so partial work survives.
- Subagents can't write `.md` files here, so put the narrative in your final
  message (short: top 5 leads, method, dead ends).
- Privacy: no humans' names; GPT-5.6 Terra and Luna only in aggregates; no
  customer names.
- Time budget: ~1.5–2 hours. Stop and report rather than overrun.
