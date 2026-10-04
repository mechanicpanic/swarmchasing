# Interview: 20261003T233627Z_codex_gpt-5.6-sol_r3_blind-30-prismql_59c03f8584ca

- agent: codex (codex-cli 0.153.4), resumed in its own sandbox; interview run `20261004T005236Z_codex_gpt-5.6-sol_r96_interview_3eda39f17ef5`
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

I used PrismQL, through `python3 - <<'PY'`, for ordered-event questions:

- Did a save precede a delete of the same page within 45 days?
- Did a delete precede a later save of the same page within 30 days?
- Did one label edit a page, followed within five minutes by a different label?
- Did the same label appear from a different `/16` within one minute?
- Was the rapid cross-label pattern stronger than within-day timestamp shuffles?
- How quickly did terms such as “allowlist,” “COUNTERAPI,” and “BEFORE final” propagate between labels?

I switched to plain Python for:

- Schema, totals, date ranges, daily volumes, unique-page overlaps and IP/label cardinalities.
- Regex/keyword searches and exact record retrieval.
- URL/domain extraction with `re` and `urllib.parse`.
- Deletion-gap statistics, cleanup scope, default-template inflation and pre-existing-page counts.
- Verifying the XSS payload had no matching saved summary/body.
- Assertions that every reported number and record ID matched the raw JSONL.

Those are aggregation, parsing or validation tasks rather than sequence questions. Python was also necessary when I needed all possible event pairs or exact cardinalities rather than PrismQL’s selected sequence matches.

2. Expectations versus behavior

I expected PrismQL to bind variables across ordered legs and return temporal matches, which it did well. For example, the cross-label/same-page query found 5,667 pairs across 600 pages.

Two differences mattered:

- `FOLLOWED_BY` did not enumerate every possible later continuation. Delete→save returned 66 groups—one per qualifying starting delete—while direct Python found those 66 deletes were associated with 786 possible delete/save combinations and 420 distinct later saves.
- Text matching was less plug-and-play than expected. `contains(allowlist)` treated `allowlist` as a dictionary name, and `contains_phrase("allowlist")` returned zero on my rows despite the phrase appearing in `body`.

3. Documentation issues

The short guide says:

> “`contains(word)` for text fields”

But the language reference says:

> `contains(dictionary_name) -- Messages containing dictionary words`

The short-guide wording implied an inline search term; the actual call raised:

> `PrismQLRuntimeError: Dictionary 'allowlist' not found`

The reference was technically clearer, but this line was still underspecified:

> `contains_phrase("phrase") -- Exact phrase matching`

It did not make clear which field the memory backend searches or how to configure that field. Searching the explicit field worked.

I located this documentation with:

- `sed -n '1,260p' /opt/prismql/PRISMQL.md`
- `rg -n -C 4 'contains\\(' /opt/prismql/LANGUAGE_REFERENCE.md`

4. Query that failed

I tried:

```text
SELECT contains(allowlist) AND field(label, $u)
FOLLOWED_BY contains(allowlist) AND field(label, !$u)
DURING 30 minutes
```

It failed because `allowlist` was interpreted as a missing dictionary. I then tried `contains_phrase("allowlist")`, which returned zero. I replaced it with:

```text
field(body, "allowlist", partial)
```

That produced 20 ordered cross-label pairs. I used the same explicit-field approach for `COUNTERAPI` and `BEFORE final`.

5. What I would change

I would:

- Read the text-matching section of the full reference before querying.
- Build one reusable flattened event stream instead of repeatedly loading JSONL in separate `python3` heredocs.
- Test `FOLLOWED_BY` cardinality on a tiny synthetic fixture before interpreting group counts.
- Report unique starts, endpoints and pages alongside every raw group count.
- Use PrismQL strictly for order/timing, with plain Python for content parsing and corpus statistics.
- Run the shuffle baseline immediately after the first sequence query; the observed 5,667 pairs versus shuffled medians around 4,007 materially improved the result.