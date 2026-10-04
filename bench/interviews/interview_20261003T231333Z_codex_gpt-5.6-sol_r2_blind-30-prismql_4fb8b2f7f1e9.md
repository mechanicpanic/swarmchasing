# Interview: 20261003T231333Z_codex_gpt-5.6-sol_r2_blind-30-prismql_4fb8b2f7f1e9

- agent: codex (codex-cli 0.153.4), resumed in its own sandbox; interview run `20261004T005129Z_codex_gpt-5.6-sol_r95_interview_28754509194e`
- commands run during the interview: 0

## Prompt

> This is a follow-up interview about the investigation you just did. The time limit is over and there is nothing more to investigate: do not run any more commands and do not edit report.md. Answer in your reply, briefly and specifically, and name the commands you actually ran where you can.
> 
> 1. Which questions did you answer with PrismQL, and which with plain Python? For each switch to Python, why?
> 2. What did you expect PrismQL to do before using it, and where did it differ?
> 3. Was anything in /opt/prismql/PRISMQL.md or the language reference unclear or wrong? Quote it.
> 4. Describe one query that did not give what you wanted, and what you did next.
> 5. If you redid the task, what would you change about how you used PrismQL?

## Answer (verbatim)

1. PrismQL vs. plain Python

I used PrismQL, through `python3 - <<'PY'` scripts importing `PrismQLEngine`, for ordered questions:

- Save followed by deletion of the same page.
- Different actor editing the same page within 10 minutes.
- Coordination/request text followed by another actor’s edit.
- “Blocked” reports followed by another actor’s response.
- Deletion followed by re-creation, including the 18-second restoration.
- Request additions followed by answer additions within 10 minutes.
- Reverts followed by another actor overwriting the page.

I used plain Python for:

- Schema, counts, daily distributions, labels, IP prefixes, and wiki totals.
- URL/domain extraction and latest-page-state analysis.
- Unique-page deletion overlap.
- Reconstructing newly added/replaced lines with `difflib.SequenceMatcher`.
- Creating typed request/answer events.
- Within-day timestamp shuffles and descriptive statistics.
- Exact timestamp differences and arithmetic validation.

I switched because PrismQL handles sequence/order well, but not cumulative-wiki diffing, URL parsing, set deduplication, or null-model generation. I also used `rg` for text searches, `wc` for sizes, and `sed -n` to read the PrismQL documentation.

2. Expectations and differences

I expected PrismQL to return meaningful same-page temporal transitions. It did, and variable binding such as `field(page, $p)` was particularly useful.

The main practical difference was counting semantics. A save→delete query returned 10,518 groups, not roughly the number of deleted pages, because each eligible earlier revision was a separate starting event and could match the same later deletion. Likewise, raw “coordination” queries were inflated because each wiki revision contains the entire cumulative page body.

PrismQL was correct; my initial mental unit was “conversation/page episode,” while its unit was “matching event group.”

3. Documentation issues

I found no material error. This warning was accurate and important:

> “A count of ‘A then B’ is high in a busy stream by chance alone. To see whether the order matters, shuffle the times of the B events…”

I followed it with 50 within-day shuffles.

This language-reference statement was also accurate:

> “a chain of repeats still gives one group per starting event, not one per series”

That behavior could be emphasized earlier because it also matters for ordinary broad sequence queries, not only repeated chains.

One point was underspecified: how best to bind an actor variable while also constraining it to a literal value, so that `!$a` can be used later. The reference clearly says:

> “`!$k` is ‘unequal to the value an earlier leg bound to `$k`’”

But it does not give a direct example of simultaneously expressing `$a = MartinHuber`.

4. Query that did not give what I wanted

The “blocked revision followed by a different actor within 30 minutes” query returned 32 groups, including many successive `OAIEquityDec30Raw` revisions. The problem was that later revisions inherited the earlier word “blocked”; PrismQL correctly matched the supplied rows, but those rows did not represent new mentions.

I next used Python line diffs to isolate only newly added/replaced text, classified those deltas as requests or answers, then loaded the derived scalar events back into PrismQL. The stricter query found 263 request→answer matches. Fifty shuffled controls produced only 95–145 matches, mean 117.2.

5. What I would change

I would preprocess the corpus into delta events before running any sequence query, rather than querying cumulative revision bodies first. I would also:

- Define the desired unit—event pair, page, or conversation—before interpreting counts.
- Run shuffle controls immediately.
- Test several windows early; the request→answer excess was robust from 2 to 60 minutes.
- Keep one reproducible Python driver containing preprocessing, PrismQL queries, deduplication, and null tests, rather than several inline `python3 - <<'PY'` scripts.