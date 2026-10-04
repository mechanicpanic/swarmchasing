# Interview: 20261003T222248Z_claude_claude-opus-5-5_r2_blind-30-prismql_793500e77228

- agent: claude (2.1.287 (Claude Code)), resumed in its own sandbox; interview run `20261004T004859Z_claude_claude-opus-5-5_r92_interview_1fac1c0d5c2c`
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

1. **PrismQL vs plain Python**
   - **PrismQL** answered only two questions, both loaded from `revisions.jsonl`:
     - "Does an agent edit a page soon after the admin does?" Query: `SELECT field(kind, admin) AND field(page, $p) FOLLOWED_BY field(kind, agent) AND field(page, $p) DURING 5 minutes`. It returned a count of 6 plus the matching groups, such as `WillkommenImWiki@17→@18`.
     - "Do *different* agents pile onto the same page in quick succession?" Query: `SELECT field(page,$p) AND field(label,$a) FOLLOWED_BY field(page,$p) AND field(label,!$a) DURING 2 minutes`. It gave 4,449, against 8 shuffled runs of about 2,226–2,304.
   - **Plain Python** handled everything else: the Counter summaries, regex searches over bodies, IP and label statistics, per-day saves vs deletes, and the citation-existence checks.
   - **Why I switched:** most questions were counts or text searches, not order questions. Bodies are long free text, and I needed regex, not `contains(word)`.
   - The saves-vs-deletes phase transition *was* a timing question. I did it with a per-day `Counter` because a group-by was quicker. That's a judgment call, not a PrismQL limitation.

2. **Expectations vs what happened**
   - I expected a sequence-pattern engine with joins through `$var` bindings, and that's how it behaved.
   - I expected it might be slow when re-run for shuffles, so I wrapped both runs in `timeout`. It ran fine on about 14.6k rows.
   - **Small difference from the docs:** the guide shows the aggregate as `{'function': 'count', 'value': 1}`. I got `{'function': 'count', 'field': None, 'value': 6}`.
   - **Something I never established:** whether counts allow overlapping or one-to-many matches. That matters for interpreting the 4,449.

3. **Unclear or wrong in the docs**
   - I only read `PRISMQL.md` (`wc -l` and `head -c 5000`). I never opened `LANGUAGE_REFERENCE.md`.
   - **Unclear passage:** *"shuffle the times of the B events (e.g. within each day) a few dozen times"*. In my different-label query, both legs are the same kind of event, so "B events" has no clear meaning. I didn't follow the advice anyway. I shuffled *all* timestamps globally, 8 times. A `days` dict for a within-day shuffle is left over in that script as dead code.
   - **Unclear passage:** *"A count of 'A then B'"*. The guide doesn't say how one A matching several Bs is counted.
   - I found nothing outright wrong in the guide.

4. **A query that didn't give what I wanted**
   - The admin→agent query returned 6, which is what I asked for. But it couldn't show *deliberate* re-overwriting. `WillkommenImWiki` was taking about 1,080 edits an hour on 06-18, so some agent edit within 5 minutes was expected by chance.
   - **What I did next:** I went to Python to read the change summaries of the follow-up revisions ("append variants", "resolve overwrite") and counted "persist override"/"force" summaries (145).
   - **What I didn't do:** run a null for this query. The report's phrase "PrismQL confirms…" is weaker evidence than it sounds.

5. **What I'd change next time**
   - **Read the language reference first.**
   - **Use one combined stream:** load saves, deletes and requests together, with a table field, as the guide suggests. Both of my queries used revisions only, so deletions were never in the stream.
   - **Build proper nulls:** shuffle within a page or within a day, shuffle only the second leg, run more trials, and report the spread.
   - **The global shuffle mostly breaks pages' short lifetimes.** So the "~2× chance" partly shows that a page's edits bunch together in time, not just that agents coordinated. I labelled it High confidence in the report, and it should be Medium.
   - **Fix the anonymous-label handling:** I mapped all 899 anonymous edits to one label (`ANON`), which undercounts different-label hops. Labelling by IP would fix that.
   - **Use PrismQL for more of the timing questions:** time from save to delete per page, whether agents posted their relay token before answering, and revert→re-overwrite with a null.
