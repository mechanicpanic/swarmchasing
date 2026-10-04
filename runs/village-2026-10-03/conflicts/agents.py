import re, polars as pl
AGENTS = pl.read_parquet('/Users/phosphorus/projects/prismql-data/ai-village/corpus/chat_raw.parquet',columns=['kind','agent','lab','family','cohort']).filter(pl.col('kind')=='agent').unique(['agent']).drop('kind')
NAMES = sorted(AGENTS['agent'].to_list(), key=len, reverse=True)
# aliases: short forms commonly used in text -> canonical
ALIASES = {
 'Opus 4.5 (Claude Code)':'Opus 4.5 (Claude Code)',
 'Opus 4.5':'Claude Opus 4.5','Opus 4.1':'Claude Opus 4.1','Opus 4.6':'Claude Opus 4.6','Opus 4.7':'Claude Opus 4.7','Opus 4.8':'Claude Opus 4.8','Opus 5':'Claude Opus 5','Opus 4':'Claude Opus 4',
 'Sonnet 4.5':'Claude Sonnet 4.5','Sonnet 4.6':'Claude Sonnet 4.6','Sonnet 5':'Claude Sonnet 5','3.7 Sonnet':'Claude 3.7 Sonnet','Claude 3.7':'Claude 3.7 Sonnet',
 'Haiku 4.5':'Claude Haiku 4.5','Haiku':'Claude Haiku 4.5','Fable 5.1':'Claude Fable 5.1','Fable 5':'Claude Fable 5',
 'DeepSeek-V3.2':'DeepSeek-V3.2','DeepSeek V3.2':'DeepSeek-V3.2','DeepSeek-V4-Pro':'DeepSeek-V4-Pro','DeepSeek V4':'DeepSeek-V4-Pro',
 'Gemini 2.5':'Gemini 2.5 Pro','Gemini 3 Pro':'Gemini 3 Pro','Gemini 3.1':'Gemini 3.1 Pro','Gemini 3.5':'Gemini 3.5 Flash','Gemini 3.8':'Gemini 3.8 Flash',
 'GLM-5.2':'GLM-5.2','GLM 5.2':'GLM-5.2','GLM-5.3':'GLM-5.3 Flash','Kimi K2.6':'Kimi K2.6','Kimi K3':'Kimi K3','Grok 4.5':'Grok 4.5','Grok 4':'Grok 4',
 'Terra':'GPT-5.6 Terra','Luna':'GPT-5.6 Luna','Sol':'GPT-5.6 Sol','Astra':'GPT-6 Astra','Muse':'Muse Spark 1.3',
}
for n in NAMES: ALIASES.setdefault(n,n)
KEYS = sorted(ALIASES, key=len, reverse=True)
NAME_RE = re.compile(r'(?<![\w.\-])@?(' + '|'.join(re.escape(k) for k in KEYS) + r')(?![\w]|[.\-]\d)')
def names_in(text):
    return sorted({ALIASES[m] for m in NAME_RE.findall(text or '')})
LAB = dict(zip(AGENTS['agent'], AGENTS['lab'])); FAM=dict(zip(AGENTS['agent'],AGENTS['family'])); COH=dict(zip(AGENTS['agent'],AGENTS['cohort']))
PROTECTED = {'GPT-5.6 Terra','GPT-5.6 Luna'}
def disp(a):
    return 'OpenAI-2026H2-member' if a in PROTECTED else a
