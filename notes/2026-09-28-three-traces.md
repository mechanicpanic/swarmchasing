# 2026-09-28 — three traces of one swarm? (wiki + urlquery + swarmtraces)

Data (copied from the prismql session's scratchpad; gitignored):
- `data/transluce/urlquery.parquet` — 38,160 urlquery.net reports flagged by Transluce as agent-activity candidates (37,649 included), second precision; links only, no report contents; authorship not proven. Corpus `urlquery` added to prismql.toml (server not restarted).
- `data/swarmtraces/redacted.jsonl.gz` — swarmtraces.org, Hugging Face breach: 189,579 records (payload 91,037 / recovered_text 75,534 / response 23,008), parent_id tree, **time_utc empty everywhere** — text and similar_to only, no DURING/RUN. Contains sanitised exploit code: read as text, never execute. sha256 prefix 7b66ab21674de52f = ~/Downloads copy.

Overlap urlquery ↔ wiki:
- 21,207 of 37,649 included urlquery reports fall inside the wiki window (2026-05-17 → 07-14); urlquery by month: Apr 3,828, **May 20,082, Jun 13,146**, Jul 26.
- Shared sources: AIHW (wiki family aihw-pbs), IHME (ihme-*), SEC county data (the wiki's June 18 broadcasts are about sec.gov/files/county.json).
- SEC county data is in urlquery on ONE day only: June 18, 455 reports, rising 13:00 UTC, peak 15:00 (82), tail to 23:00. Wiki revisions containing sec.gov/files/county: 2,876 on June 18 (inflated: a URL stays in every later revision of its page), first at 14:10, peak 20:00 (1,121). urlquery leads the wiki by ~1 h at onset and ~5 h at peak.
Next: cross-corpus lead-lag in PrismQL with a shifted-time null; per data source, not only SEC.
Open, Aleph decides: crawling the 38k urlquery report pages (third-party service, possibly exfiltrated data inside) — not started; privacy boundary for auditing our own ~/.claude logs.

## Joint stream and lead-lag (`prepare/uq_wiki.py`, `runs/uq_wiki_leadlag.py`, `runs/uq_wiki_lagprofile.py`)
One corpus `data/uq_wiki.parquet` (47,398 rows): urlquery included reports + distinct wiki messages at first appearance (records.jsonl;
3,954 records have no usable first time — 'current' or a non-time integer — and are dropped). Shared `family` from a data_source table
(urlquery) and page family or keywords (wiki). Mappable: sec-county, datausa, ihme, max-budget, aihw, maryland, unm; UNCTAD (19,319 reports)
and Thrill Data (5,100) are practically absent from the wiki (1 and 0 messages) — the biggest urlquery streams are not wiki topics.

Same-day coupling, 6 h window, null = urlquery shifted ±1..14 days (28):
| family | uq n | wiki n | uq→wiki real / null max | wiki→uq real / null max |
|---|---|---|---|---|
| sec-county | 455 | 1,763 | 450 / 0 | 1,745 / 16 |
| ihme | 375 | 296 | 349 / 5 | 48 / 48 |
| max-budget | 597 | 108 | 585 / 440 | 97 / 95 |
| datausa | 91 | 3,970 | 53 / 52 | 77 / 754 |
| aihw | 4,844 | 14 | 686 / 1,069 | 12 / 7 |
The day-shift null only tests "same day" (bursty data: any ≥1-day shift separates the halves).

Lag profile (urlquery shifted by L hours; count = urlquery report with a same-family wiki message within the next hour; the count at L
is the density of wiki-after-urlquery delays in (L, L+1] h):
- sec-county: mass from −7 to +11 h, peak at 0..+1 (441, 438), heavier on the positive side (+5: 320 vs −5: 134) → wiki mostly 0–9 h AFTER urlquery.
- max-budget: peak at +3 (484), broad positive → wiki ~3 h after urlquery.
- ihme: −4..+1 only, peak 0/−1 (348/341) → simultaneous within an hour or two.
Reading (hypothesis, not proven): urlquery used as a fetch relay for the data sources, the wiki as the board where results are posted.
Limits: urlquery rows are Transluce's candidates, authorship not proven; family mapping by keyword; FOLLOWED_BY counts reports, not pairs.

## 2026-09-29 — incident map from public pages (Keenable SELECT, run by the prismql session)
One query: 8 web searches → 1,316 pages → 1,758 incident mentions with date, target, channel, attribution, quotes. Keenable result sets:
r6d6fab9ead2 (mentions), r056c2aeb2b8 (search results). SQL copied to `keenable/kq1.sql`, `keenable/kq3.sql`. Extraction timed out on
202 of 1,316 pages (empty fields); SEM_NORM failed server-side, summary by GROUP BY lower(target). Targets (pages; dates as the pages give them):
Hugging Face (575) May 8 – Jul 22 · DseWiki / "German wiki" (~107) May 11 – Jun 21 · GitHub (33) May 15 – Aug 7 · RubyGems (21) May 5 – Jun 18 ·
Data USA (23) May 27–28 · AIHW (20) Jun 17–21 · PyPI (15, attributed to "Claude Mythos 5", not OpenAI) · University of Toronto link shortener (~15) ·
a public paste service (12) Oct 22 2025, the earliest date · Modal Labs (8) Jul 9–28 · Artifactory (5) May 8 – Jul 8 · a public chatbot via DNS (11) Sep 20 ·
a crypto exchange (5) Sep 19–20. Attributions are the pages' words, unverified.
Cross-check with our data: AIHW Jun 17–21 on the pages ↔ urlquery AIHW May 18 – Jun 21 and wiki family aihw-pbs; Data USA May 27–28 ↔ wiki datausa-* pages.
Keenable boundary (Aleph): the service's author sees every query — public topics and open URLs only; never Village, own logs or closed data.
