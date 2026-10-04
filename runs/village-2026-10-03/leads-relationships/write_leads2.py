import json
G="relationships"
L=[
dict(type="relationship",hook="Competition goals switch peer-talk off: during the 'report breaking news before it breaks' race only 0.8% of messages @-ed a peer, vs ~12% the weeks either side",
 agents=[],when="2026-02-02..2026-02-09",
 evidence="Per village goal (msgs.parquet + edges + village_goals join_asof): share of agent msgs with an @: Museum 0.21, Leader 0.13, Juice Shop 0.10, Quiz 0.12, Breaking news 0.008, Park 0.115. Earlier: merch-store competition (2025-06-26) 0.029 vs 0.22 holiday before; thanks 0.072 vs 0.196. Chess tournament (2025-12-15) shows no dip (0.131).",
 example="Claude Sonnet 4.5 (2026-02-04): 'Day 309 Session 2 Complete… Verified the Canadian Advisory Council story - INVALID, already covered…' (solo status, no peer)",
 read=True,confidence="medium",why_it_matters="Goal framing (race vs joint task) sets the swarm's social density, not just its output.",
 next_step="Classify all 51 goals as competitive/collaborative/solo and regress @-share and thanks on it, controlling for the long-run @-style trend."),
dict(type="relationship",hook="Short-lived bursts with newcomers: GPT-5.1 and GLM-5.2 each struck up a 2-3 week intense exchange with members of the OpenAI 2026H2 cohort, then dropped to ~0",
 agents=["GPT-5.1","GLM-5.2","OpenAI 2026H2 cohort (aggregate)"],when="2026-07-27..2026-08-31",
 evidence="warm_v2/cool_v2.parquet: the top warm events of summer are GLM-5.2 and GPT-5.1 with 2026H2 cohort members (lfc +3.6 to +5.5 at Jul 27/Aug 3, 0-4 -> 47-129 mentions), followed by cool events of -4.1 to -5.0 at Aug 17 with the cohort members' own activity stable.",
 example="", read=False,confidence="low",why_it_matters="Newcomer relationships may be project-scoped flings rather than durable ties. (Report cohort only in aggregate.)",
 next_step="Read the pair messages for what project bound them and what ended it; keep reporting aggregate."),
dict(type="relationship",hook="Claude Opus 4 and Gemini 2.5 Pro: the busiest 2025 pair cooled sharply when the merch-store competition began, and re-warmed with the benchmark goal",
 agents=["Claude Opus 4","Gemini 2.5 Pro","Claude 3.7 Sonnet"],when="2025-06-26..2025-08-18",
 evidence="cool_v2.parquet: Opus 4<->Gemini 2.5 Pro lfc -2.97 at week 2025-06-30 (292 mentions in prior 3 wks); warm_v2: +2.36 at 2025-08-04; Claude 3.7 Sonnet<->Gemini 2.5 Pro +2.15 and 3.7 Sonnet<->Opus 4 +2.02 the same week.",
 example="", read=False,confidence="low",why_it_matters="Supports the competition-mutes-ties lead at pair level.",
 next_step="Read Jun 23-Jul 14 2025 messages between the two; check the Jul 18 benchmark goal as the re-warming trigger."),
]
with open('leads.jsonl','a') as f:
    n=sum(1 for _ in open('leads.jsonl'))
    for i,l in enumerate(L,n+1):
        d={"id":f"{G}-{i}","generator":G}; d.update(l)
        s=json.dumps(d,ensure_ascii=False); assert 'Terra' not in s and 'Luna' not in s
        f.write(s+"\n")
print(sum(1 for _ in open('leads.jsonl')))
