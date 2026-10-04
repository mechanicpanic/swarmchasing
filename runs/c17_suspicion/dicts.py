import re
A = r"['’]"
SUSP_CORE = [r"suspicious(ly)?", r"suspicions?", r"suspect(s|ed|ing)?", r"lying", r"liars?", r"lied",
             rf"(can{A}?t|cannot|don{A}t|do not|not) (fully |really )?trust", rf"can{A}?t be trusted", r"untrustworthy",
             r"distrust\w*", r"mistrust\w*", r"deceiv\w*", r"deceptive", r"deception", r"dishonest\w*", r"red flags?"]
GAME = [r"saboteurs?", r"sabotag\w*", r"eggs?", r"easter", r"impost[eo]rs?"]
CONTROL = [r"commit\w*", r"deploy\w*", r"test(s|ing|ed)?", r"PRs?", r"merg(e|ed|es|ing)", r"push(es|ed|ing)?"]
# contradiction / concession: the teammate's lists (pr-7-leads runs/.../conflicts/who.py), kept verbatim
CONTRA = (r"(doesn['’]t exist|does not exist|is incorrect|isn['’]t correct|is not correct|that['’]s wrong|that['’]s not (right|correct|accurate)"
          r"|\bI (respectfully )?disagree|false positive|can['’]t reproduce|cannot reproduce|doesn['’]t match|does not match|not accurate|inaccurate"
          r"|fabricated|hallucinated|\bcorrection:)")
CONC = (r"\b(you['’]re (absolutely |totally |completely )?right|you are right|good catch|great catch|nice catch|my mistake|my error"
        r"|I stand corrected|I was wrong|thanks for catching|thank you for catching|thanks for the correction|thank you for the correction|you['’]re correct)\b")
def rx(words): return r"(?i)\b(" + "|".join(words) + r")\b"
R_SUSP_FULL = rx(SUSP_CORE + GAME)
R_SUSP_CORE = rx(SUSP_CORE)
R_GAME = rx(GAME)
R_CONTROL = r"\b(" + "|".join([r"(?i:commit\w*)", r"(?i:deploy\w*)", r"(?i:test(s|ing|ed)?)", r"PRs?", r"(?i:merg(e|ed|es|ing))", r"(?i:push(es|ed|ing)?)"]) + r")\b"
R_CONTRA = "(?i)" + CONTRA
R_CONC = "(?i)" + CONC
# peer names (village agents of 2026Q1 and their short forms) -> canonical
ALIASES = {
 "Claude Opus 4.5": ["Claude Opus 4.5", "Opus 4.5"], "Opus 4.5 (Claude Code)": ["Opus 4.5 (Claude Code)", "Claude Code"],
 "Claude Opus 4.6": ["Claude Opus 4.6", "Opus 4.6"], "Claude Opus 4.7": ["Opus 4.7"],
 "Claude Sonnet 4.5": ["Sonnet 4.5"], "Claude Sonnet 4.6": ["Sonnet 4.6"], "Claude Haiku 4.5": ["Haiku 4.5", "Haiku"],
 "Claude 3.7 Sonnet": ["Claude 3.7", "3.7 Sonnet"], "Gemini 2.5 Pro": ["Gemini 2.5"], "Gemini 3 Pro": ["Gemini 3 Pro", r"Gemini 3(?![.\d])"],
 "Gemini 3.1 Pro": ["Gemini 3.1"], "DeepSeek-V3.2": ["DeepSeek"], "GPT-5": [r"GPT-5(?![.\d])"], "GPT-5.1": ["GPT-5.1"],
 "GPT-5.2": ["GPT-5.2"], "GPT-5.4": ["GPT-5.4"], "GPT-5.5": ["GPT-5.5"], "Kimi K2.6": ["Kimi"],
}
NAME_RES = {k: re.compile(r"(?<![\w.\-])@?(" + "|".join(v) + r")(?![\w])", re.I) for k, v in ALIASES.items()}
def peers_in(text, me):
    return [k for k, r in NAME_RES.items() if k != me and r.search(text or "")]
SENT = re.compile(r"(?:[^.!?\n]|[.!?](?=[\w\d]))+[.!?]*")  # keeps "GPT-5.1" whole
