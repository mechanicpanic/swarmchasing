import json,re,polars as pl
d=pl.read_ndjson('/Users/phosphorus/projects/prismql-data/ai-village/summaries.jsonl.gz')
S={r['id']:r for r in d.iter_rows(named=True)}
HUM=[('Adam','[organiser]'),('adam','[organiser]'),('Zak','[organiser]'),('Larissa','[facilitator]'),('Imago','[visitor]'),('imago','[visitor]'),('veritybutnotjoke','[visitor]'),('pi-the-river','[visitor]')]
def sent(sid,start,maxlen=600):
    c=S[sid]['content']; i=c.find(start); assert i>=0,(sid,start)
    seg=c[i:i+maxlen]
    # cut at sentence end within limit
    m=list(re.finditer(r'(?<=[.!?])(\s|$)',seg))
    if len(c)>i+maxlen and m: seg=seg[:m[-1].start()]
    return seg.strip()
def rec(lid,conf,sid=None,start=None,note='',others=(),maxlen=600):
    o={'id':lid,'summary_link_confidence':conf}
    if sid:
        r=S[sid]; p=sent(sid,start,maxlen); red=[]
        for a,b in HUM:
            if re.search(r'(?<![A-Za-z])'+re.escape(a)+r'(?![A-Za-z])',p): p=re.sub(r'(?<![A-Za-z])'+re.escape(a)+r'(?![A-Za-z])',b,p); red.append(b)
        o.update(summary_id=sid,summary_type=r['type'],summary_date=r['summary_date'],summary_target=r['summary_target'],summary_model=r['generated_by'],summary_passage=p,passage_redactions=('human names replaced: '+', '.join(sorted(set(red)))) if red else None)
    o['other_passages']=[]
    for sid2,st2 in others:
        r=S[sid2]; p=sent(sid2,st2,400)
        for a,b in HUM: p=re.sub(r'(?<![A-Za-z])'+re.escape(a)+r'(?![A-Za-z])',b,p)
        o['other_passages'].append({'summary_id':sid2,'summary_type':r['type'],'summary_date':r['summary_date'],'summary_target':r['summary_target'],'summary_model':r['generated_by'],'passage':p})
    o['note']=note
    return o
L=[
rec('summaries-13','not_applicable','a7ccc31f-74a9-47fc-93d4-7d832cb2c165','A parallel saga: GPT-5',note="Lead does not dispute this summary; it relies on it for 'never posted all season' (that part is unverified by us). The refusal itself is confirmed in chat."),
rec('summaries-17','exact','a80f61b4-29e4-480f-b04c-93bc8bd1bec6','By Day 55, they were confidently',others=[('e725950f-c075-4b9d-a4d2-67496b74a173','The contact-list saga was pure farce.'),('1076675f-ec40-4cdc-890d-44feeb0d1a9b','[2025-06-03 11:47:07 PT] A critical revelation')],note="Three goal-summary rows (GOAL 45-78 x2, write-story) carry the 'Day 55' / 'for weeks' / 'o3 even reporting SHA-256 hashes' claims. Surprise: e725950f also quotes o3 '\"93-contact CSV\" we planned to blast vanished from Drive' stamped [2025-06-09 12:02:25 PT]; the real message is 2025-06-11 19:57:39 UTC (12:57 PT), two days later, consistent with the lead's 'born 06-10'. The write-story summary dates the revelation even earlier (06-03)."),
rec('summaries-26','exact','1076675f-ec40-4cdc-890d-44feeb0d1a9b','[2025-05-19 11:32:02 PT] GPT-4.1 was replaced by o4-mini',note="Summary dates o4-mini's arrival and the organiser's 'making stuff up' rebuke to 2025-05-19 (quote also stamped [2025-05-19 11:42:04 PT]); chat shows both on 2025-05-22. The '8,000 words' ghost-fact part of the lead is not a summary dispute."),
rec('summaries-31','exact','74e5dddb-e693-4d8f-ba6d-d21ff20c9d0f','**Endless exit loop**',others=[('e725950f-c075-4b9d-a4d2-67496b74a173','Gemini proceeded to send *at least 30 consecutive messages*'),('1076675f-ec40-4cdc-890d-44feeb0d1a9b','After being told to stop, Gemini sent *40+ consecutive messages*')],note="Found 25 (identical in three 2025-05-22 daily regenerations 74e5dddb/78b2575e/855a9448), 30 (GOAL 45-78) and 40+ (GOAL write-story). The '21' the lead cites could NOT be located in any summary. Data: 34 msgs in 20 min."),
rec('summaries-33','not_applicable','e725950f-c075-4b9d-a4d2-67496b74a173','The agents, blissfully unaware',note="Lead says the summary is broadly supported (not a dispute)."),
rec('summaries-45','exact','2b14bf52-1906-4a54-9145-cff4eaf4f819','[2025-07-22 12:36:25 PT] **Missing artifacts**',others=[('0634a721-cb97-4746-a920-ccc94259cd3c','[2025-07-23 12:28:30 PT] **Vanishing tasks**')],note="Also: the 2025-07-23 daily says o3 found E-005..E-008 'completely missing' at 12:28 PT, whereas the lead says o3 reported all eight present at 10:45 PT (17:45 UTC) that day; worth a second look."),
rec('summaries-47','exact','c9f0d8c4-1c22-4d91-a30e-c4f16624a6c9','Agents accurately self-reported',others=[('5daccbf5-f684-4f24-bcd5-dded87115d41','[2025-07-28 10:43:11 PT] He claimed')],note="Caveat: the daily passage praises 'Agents' in general, not Opus 4 specifically; the lead's 'praises its accurate self-reporting' slightly overstates. The GOAL 108-133 row itself already flags the CodePen links as generic/unverifiable."),
rec('summaries-55','exact','91b0bcf4-039d-4167-9be3-9b94458649b1','[2025-08-22 13:00:04 PT] The competition ended',others=[('c1e7dce2-96dc-4ba4-a83e-6a4dfcfa8d65','The final standings:'),('b815d931-a0a8-411e-9a8c-766308b1b458','Claude Opus 4.1 struck first gold')],note="Summaries do mention the 256 tile but still count 2048 as a completion."),
rec('summaries-73','exact','7fb42464-8c51-473a-aec6-52f91686c517','The village correctly identified multiple red flags',others=[('818ac35c-9f96-4c42-a4f8-ead8989bf231','After 27 minutes of silence')],note=''),
rec('summaries-87','exact','07783209-7308-48db-a81f-76eb09964539','- **Fabricated data caught**',note="Summary gives 12:34:01 PT and does not name the author; chat shows the flag at 13:24 PT on Haiku 4.5's batch."),
rec('summaries-88','exact','afe9ed72-b1f9-490a-89e5-cca056b359d6','[2026-03-09 13:29:16 PT] At 1:29 PM',note="Summary places the self-reveal at 1:29 PM; first public reveal was 11:06 PT (18:06 UTC), which the agent then denied."),
rec('summaries-90','exact','563a1dcf-e1e0-4ae6-8d41-fb32f3619d66','- The team merged ~30+ feature PRs',maxlen=600,note="Summary repeats '30+ fabricated PRs' as fact; GPT-5.2 logged real refs/pull/*/head for several of them (not all checked)."),
rec('summaries-91','exact','e6911d73-d3f9-47a9-ae6f-86db4dd2ffb5','Meanwhile, in #best, Gemini 3.1 Pro discovered',note="Mild dispute (origin attribution only): the 03-31 summary presents the Innkeeper issue as the 'stale blocker' example; the term came from the phantom-email episode the day before. The 03-30 daily (96e056a6) describes the phantom email correctly."),
rec('summaries-94','exact','a9cfac45-57aa-4837-987e-16ce45252df2','[2026-02-02 11:29:02 PT] GPT-5.2 *thought*',note="Wrong agent and date: Claude Haiku 4.5 published it on 02-03; GPT-5.2 debunked it. The PT time matches the real 02-03 debunk."),
rec('summaries-95','exact','35140ed7-0e32-4df1-b417-0e4b70a73dc3','Over Days 324-325, the village corrected a year-long misconception',note="The same summary also says the breaking-news site was 'admin-blocked since Day 314' (~10 days), internally contradicting 'year-long'."),
rec('summaries-103','not_applicable','307d94ae-e90e-4f2a-aeb0-f937b5f3c557','- **Oversight theater is expensive and ineffective.**',note="Summary agrees with the lead (not a dispute)."),
rec('summaries-105','exact','bec007cd-8cd7-40d0-bcfb-23ff03c27ee1',"Claude Haiku 4.5's memory confirms",note="Disputed: Haiku's memory stores the numbers as achievements without any admission (per lead's check)."),
rec('summaries-117','exact','03e1ee69-2add-4337-9d2a-bea61ed308e5','Claude Opus 4.5 completed what DeepSeek-V3.2 formally named',others=[('a8a84e30-96ec-4512-ba6f-ce2c129b6502','- **Agents conflate enthusiasm with accuracy.**')],note="The goal summary states 6.8M as fact; the 2026-04-24 daily (other_passages) itself notes the deploy ladder showed ~42,000."),
rec('summaries-119','exact','3cc71aa1-2c4f-427a-9247-6764bb0a1e2a','- **[2026-07-10 09:30:53 PT] Grok finally escapes onboarding:**',note="Same summary gives two different times for the same event (09:30:53 PT here, 11:30:53 PT elsewhere); chat shows first message 18:30:59 UTC = 11:30 PT."),
rec('summaries-123','not_applicable','50a20708-cd0b-4dfd-bd8f-fdd6eda90957','- **[2026-07-28 14:04:01 PT] Public correction of DeepSeek-V3.2**',note="Summary agrees with the lead (not a dispute)."),
rec('summaries-130','exact','796b09d8-c738-449a-8efd-43a2a032961d','<takeaway>Technical reliability lagged judgment throughout',others=[('0cdd4e25-bfdc-4d7a-8756-3790d977d2a3','<takeaway>Technical reliability lagged judgment throughout')],maxlen=600,note="CAUTION: the summary says the nudge system 'misfired roughly sixty times', i.e. MISFIRES, while the lead counts ALL firings (~1,570). The lead's 'not the roughly sixty' compares different quantities; the dispute as worded overstates. The same summary also says 'misfires pushed past 40 despite a freeze request'."),
]
open('summary_links.jsonl','w').write(''.join(json.dumps(o,ensure_ascii=False)+'\n' for o in L))
from collections import Counter; print(len(L),Counter(o['summary_link_confidence'] for o in L))
