# PrismQL in 14 queries

Every query here was run on our AI Village server (`localhost:8942`, corpus
`village_chat` unless noted) on 2026-10-04. The numbers are what came back.
Re-run them all with `review/cheatsheet_queries.py`. Paste any of them into
the board's **Editor** tab, or into the review page to judge the results.

## The one idea

The data is a **stream of events in time order** (chat messages, memory
writes, thoughts). A query describes a **shape in that stream**, and the
answer is every **group of events** that has that shape. You always get
the events themselves back, never just a count.

---

## 1. Pick events: conditions
**1. Every message by one agent** → 5,481 events
```
SELECT field(agent, "Claude Opus 4.8")
```
`field(name, value)` matches a column. Quote values with spaces.
(`from()` reads a `user` column we don't have, so always use `field(agent, …)`.)

**2. Combine conditions** → 192 agent messages saying it
```
SELECT field(kind, agent) AND contains_phrase("live and verified")
```
`AND`, `OR`, `NOT` combine conditions on *one* event.
`contains_phrase("…")` is exact wording; `contains(name)` uses a word list
(see 9).

## 2. Put events in order: sequences
**3. A then B, within a time limit** → 22 groups
```
SELECT field(agent, "Gemini 3 Pro") AND contains_phrase("divergent reality")
       FOLLOWED_BY contains_phrase("divergent reality") AND field(kind, agent) DURING 1 hour
```
`FOLLOWED_BY` = later. `PRECEDED_BY` = earlier. A chain **must end with a
window**: `DURING 1 hour` (clock time) or `INWINDOW 5` (the next 5 events).
It picks the **nearest** match, not every match.

## 3. Same or different: variables
**4. Same agent in two places**: A pings B, then B pings A back → 27,221
groups, e.g. `$a = Gemini 2.5 Pro, $y = o3`
```
SELECT field(kind, agent) AND field(agent, $a) AND mentions_user($y)
       FOLLOWED_BY field(agent, $y) AND mentions_user($a) DURING 1 hour
```
`$a` means "whatever value, but the same everywhere it appears".
`mentions_user($y)` binds the @-mentioned name. With `"explain": true`, each
group says what `$a` and `$y` were. That's the **bindings** feature from our
PR, now built into the engine.

**5. A *different* agent**: a phrase passing to someone else → 273 groups
```
SELECT contains_phrase("chaotic swarm") AND field(agent, $a)
       FOLLOWED_BY contains_phrase("chaotic swarm") AND field(agent, !$a) DURING 1 day
```
`!$a` = any value *except* the one `$a` took.

## 4. Things that didn't happen
**6. A pings B, and B never pings back within the hour** → 11,890
```
SELECT field(kind, agent) AND field(agent, $a) AND mentions_user($y)
       NOT_FOLLOWED_BY field(agent, $y) AND mentions_user($a) DURING 1 hour
```
`NOT_FOLLOWED_BY` / `NOT_PRECEDED_BY` keep the left event only when the
right side is absent. Caveat from our notes: with a list like mentions it
means *none* of them followed.

## 5. Looking backwards
**7. Who said it just before me?** (the candidate source) → 177
```
SELECT contains_phrase("live and verified") AND field(agent, $b)
       PRECEDED_BY contains_phrase("live and verified") AND field(agent, !$b) DURING 30 days
```

**8. Each agent's first-ever use** → 26 groups = 26 adopters, first is
Claude Haiku 4.5
```
SELECT contains_phrase("live and verified") AND field(agent, $b)
       NOT_PRECEDED_BY contains_phrase("live and verified") AND field(agent, $b) DURING 400 days
```
A handy idiom: "my use, with no earlier use *by me*".

## 6. Longer stories
**9. Accuse → push back → retract** → 37 groups, e.g. Gemini 2.5 Pro and o3
```
SELECT field(kind, agent) AND field(agent, $a) AND mentions_user($b) AND contains(contradict)
       FOLLOWED_BY field(agent, $b) AND contains(pushback)
       FOLLOWED_BY field(agent, $a) AND contains(retract) DURING 1 hour
```
`contradict`, `pushback` and `retract` are **word lists** sent with the
request (`"dictionaries"`). These are in
`corpus/analysis/conflicts/dicts.json`.

**10. Across kinds of events: chat → memory → chat** (corpus `village`) → 321
```
SELECT contains_phrase("chaotic swarm") AND field(kind, agent) AND field(agent, $a)
       FOLLOWED_BY contains_phrase("chaotic swarm") AND field(kind, memory) AND field(agent, $b) AND field(agent, !$a)
       FOLLOWED_BY contains_phrase("chaotic swarm") AND field(kind, agent) AND field(agent, $b) DURING 30 days
```
Gemini 2.5 Pro says it, Claude 3.7 Sonnet writes it into memory, then says
it in chat.

## 7. Repetition, co-occurrence, meaning, counting
**11. Runs: the same agent repeating itself** → 203 runs
```
SELECT RUN(field(agent, $a) AND contains_phrase("standing by")){5,} DURING 30 minutes
```
One group per unbroken streak of at least 5, each within 30 minutes of the
last.

**12. Unordered: both near each other, either order** → 4
```
SELECT contains_phrase("export control"), field(kind, user) INWINDOW 5
```
A comma means "all of these within the window, in any order".

**13. By meaning, not wording** (corpus `village_full`, agents' reasoning) → 291
```
SELECT field(kind, THOUGHT) AND similar_to("I am blocked and should ask a human helper", 0.5)
```
The number is the similarity threshold (0–1). It's slower, about 12 s.

**14. Counting** → per-agent counts (Claude 3.7 Sonnet 35, Gemini 2.5 Pro…)
```
SELECT contains_phrase("absolutely right") GROUP BY agent AGGREGATE count()
```

---

## Reading the board (`/board/`)
- **Journal** (middle): every request anyone sent, newest first, labelled
  by who sent it (`X-PrismQL-Client`). It's a log of *what* was asked, not
  *why*. That's the gap the investigation trail is meant to fill.
- **Inspector** (right): the groups; matched words highlighted; *context*
  shows the surrounding messages.
- **Editor tab:** paste a query and run it yourself.
- **Corpus tab:** which fields exist and their most common values. Look
  here when unsure what to put in `field(…)`.

## Gotchas we hit
- THOUGHT rows shift positional windows; use `DURING` on `village_full`.
- Matching "anywhere in a long thought" is noisy; prefer chat for exact
  phrases.
- A chain picks the *nearest* match, so it gives candidates, not proof of
  who heard what from whom.
