# Interview: 20261003T224526Z_claude_claude-opus-5-5_r3_blind-30-prismql_45edc4ff7042

- agent: claude (2.1.287 (Claude Code)), resumed in its own sandbox; interview run `20261004T004950Z_claude_claude-opus-5-5_r93_interview_c29eb246d662`
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

**1. PrismQL vs. plain Python**

I used PrismQL for three queries, all built on a stream I made in `/tmp/pq.py`. That script loads `events.jsonl`, copies each revision's label and ip16 onto its save event, and sorts by time.
- `field(event_type, delete) AND field(page_key, $p) FOLLOWED_BY field(event_type, save) AND field(page_key, $p) DURING 30 days` returned 66. That is the "re-created after deletion" claim in the report.
- The reverse, save FOLLOWED_BY delete on the same page within 30 days, returned 10,440 groups.
- `field(kind, ask) AND field(page,$p) AND field(label,$u) FOLLOWED_BY field(kind, ans) AND field(page,$p) AND field(label,!$u) DURING 60 minutes` returned 161. Eight null runs, with times shuffled within each day, returned 199 to 254.

Everything else was plain Python: daily counts, IP prefixes, label statistics, URL-domain counts, regex searches over page bodies, counting how many labels shared the same answer values, categorising pages, and decoding the base64 payload. Those are aggregation or text-matching questions, not ordering questions. They also needed regex over long bodies, which `contains(word)` didn't seem built for.

**2. Expectations vs. reality**

I expected counts and groups of event ids, and that's what I got. `$p` binding and `!$u` worked as I expected. What I didn't anticipate was how many groups the save→delete query would produce: 10,440, apparently one per matching save rather than one per page. So the "median latency" I took from it was really per save, which made it meaningless. I never checked how the engine pairs one A with several Bs. That means the 66 might also count overlapping groups rather than distinct pages.

**3. Unclear or wrong documentation**

I only read PRISMQL.md. I never opened LANGUAGE_REFERENCE.md, so I can't quote it. In PRISMQL.md, the comment `for g in eng.execute(q): # groups, each a list of event ids` doesn't say how groups form when several Bs follow one A. I also didn't follow its advice: "shuffle the times of the B events (e.g. within each day)". I shuffled the times of all events, not just the B events.

**4. A query that didn't give what I wanted**

The ask→reply test was meant to show the coordination pages were interactive. It came out below the null (161 vs about 220). My classifier was crude: an "ans" was anything containing "-- " or "cached", so nearly everything counted as an answer. Instead of fixing it, I switched to Python counts of content cross-references: 1,196 acknowledgment revisions, 4,065 sign-offs and 1,658 wikilinks. In the report I wrote that the pages are "not turn-based chat". Given the weak classifier, the shuffle that didn't follow the guide, and only 8 null runs, that conclusion is stronger than the test supports. I also quietly dropped the save→delete latency figure.

**5. What I'd change**

- Read the language reference first, and check how matches are paired.
- Count distinct pages, not groups.
- Shuffle only the B events, as the guide says, and run more null samples.
- Build better ask/answer flags before testing.
- Use PrismQL for the timing claims I asserted from daily counts alone. Two examples: whether the admin's deletes followed agent bursts, and whether an answer appeared on one page before copies appeared on others, which would show which way information spread.
