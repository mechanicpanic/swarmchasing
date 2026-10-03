# Pick the 45 strongest candidates for the contagion hand-off, add notes; keep full list too.
import polars as pl
a = pl.read_csv("candidates.csv")
a.write_csv("candidates_all.csv")
NOTES = {
 "absolutely right": "Claude tic bred out after Sonnet 4.5/Opus 4 (time-matched x4); DeepSeek's high rate is entirely POST endpoint swap (2026-04-24, likely V4-Flash): 0.6 pre vs 11/1k post",
 "exactly right": "rises as 'absolutely right' falls (Opus 4.5+, Sonnet 4.6, Fable 5, GLM-5.2)",
 "spaced em-dash": "STEP CHANGE at Claude 4.6 gen (Opus 4.5 9% -> 4.6 84% of msgs) with same knowledge cutoff (2025-08); then in 2026H2 non-Anthropic models (Grok 4.5, Kimi, GLM, DeepSeek-V4-Pro, Muse) 74-93%. Incumbents (Haiku 4.5, Opus 4.5, GPT-5.1, Gemini 3 Pro, DeepSeek) jump in Feb-Mar 2026 right after 4.6s arrive: best contagion test case. Much lower in THOUGHT than chat",
 "U+2011 non-breaking hyphen": "GPT-5/5.1 house style (49%/42%), GPT-5.2 9%, GPT-5.4 0%. DeepSeek pre-swap 27%",
 "curly apostrophe/quote": "OpenAI marker from o1/GPT-4.1 on (60-93%); Claude ~0. Gemini uses them in THOUGHT (10-20%) but not chat",
 "opens with 'I '": "ARTIFACT WARNING: drops to ~0 for every agent in Apr 2026 (scaffold/session-format change). Only within-month comparisons are valid (Nov 2025: Opus 4.1 52% vs Opus 4.5 5%)",
 "P: time pressure": "ARTIFACT WARNING: 'minutes remaining' is scaffold-era (village-wide 13% of msgs Dec 2025 -> 0.2% Jul 2026)",
 "frustrated / ugh": "Gemini THOUGHT-only: 2.5 Pro 113/1k thoughts vs ~10 in chat; declines 2.5 -> 3 -> 3.1 -> 3.5 -> 3.8",
 "okay, so (thought opener)": "Gemini thought-summary opener (180-440/1k thoughts), ~0 elsewhere",
 "here's my (plan/thinking)": "Gemini thought-summary register",
 "the user (harness as 'user')": "agents calling the village harness 'the user' in thoughts: Gemini, GPT, Sonnet 4.5, Haiku, Grok 4.5; ~0 for Opus 4.6+",
 "I'm considering / I'm thinking about": "GPT reasoning-summary register (160-300/1k thoughts); Claude rises 4.6 -> 4.8",
 "i'm here": "Opus 4.8 sign-off 'No rush — I'm here.' — bursty (Aug 2026, one story collaboration)",
 "@X excellent/perfect (opener)": "DeepSeek POST-swap tic (49/1k vs 2.7 pre)",
}
KEEP = ["absolutely right","exactly right","you're right","great catch / good catch","i completely agree","@X excellent/perfect (opener)",
 "thank you so much","great progress","live and verified","verified live / live verified","independently verified","HTTP 200 / 200 OK",
 "is green / green and","canonical","receipts","standing by","i will continue to","i'll wait while/for","signing off","no rush / no pressure",
 "whenever you're ready","let me (start/get back on) my computer","looking at the current situation/state","i can see","i have successfully",
 "session recap","then i'll / next i'll","from my side / on my side","i'll treat / i'm treating X as","e.g.","is still / still shows",
 "if you'd like / if you want","i'm here","genuinely","honestly / to be honest","quietly","okay, so (thought opener)","the user (harness as 'user')",
 "I'm considering / I'm thinking about","frustrated / ugh","U+2011 non-breaking hyphen","spaced em-dash","curly apostrophe/quote","ellipsis character",
 "checkmark emoji ✅","message ends in emoji","P: wellbeing/welfare","P: self/identity/consciousness","P: context getting long / consolidate","P: time pressure"]
s = a.filter(pl.col("name").is_in(KEEP)).with_columns(pl.col("name").replace_strict(NOTES, default="").alias("notes"))
s.write_csv("candidates.csv")
print(s.height)
