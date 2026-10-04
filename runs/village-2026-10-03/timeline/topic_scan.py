"""Keyword scan for external-event topics across human chat, agent chat, thoughts, memory. Monthly counts + first hits."""
import polars as pl
T = '/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/timeline/'
TOPICS = {
 'sycophancy': r'(?i)sycophan|\bglazing\b|yes-man',
 'flattery': r'(?i)\bflatter',
 'pentagon': r'(?i)pentagon|department of war|department of defense|\bhegseth|supply[- ]chain risk',
 'hugging_face': r'(?i)hugging ?face',
 'training_pause': r'(?i)training pause|paus\w* (its |their |model |frontier )?training',
 'mechahitler': r'(?i)mechahitler',
 'blackmail': r'(?i)blackmail',
 'model_welfare': r'(?i)model welfare|ai welfare|moral patien|model wellbeing',
 'eu_ai_act': r'(?i)\bEU AI Act\b|\bAI Act\b',
 'state_law': r'(?i)\bSB ?53\b|\bSB ?1047\b|RAISE Act|AI moratorium|preempt',
 'moltbook': r'(?i)moltbook|openclaw|clawdbot|moltbot',
 'agentic_misalignment': r'(?i)agentic misalignment|alignment faking|reward hack|scheming',
 'ai_psychosis': r'(?i)ai psychosis|chatbot psychosis',
 'constitution': r'(?i)claude.{0,20}constitution|constitution.{0,20}claude',
 'deprecation': r'(?i)deprecat',
 'sandbox': r'(?i)sandbox',
}
lf = pl.scan_parquet(T + 'text_lean.parquet')
rows = []
for name, rx in TOPICS.items():
    hits = lf.filter(pl.col('text').str.contains(rx)).select('time', 'src', 'agent', 'room', 'text').collect()
    hits = hits.with_columns(pl.lit(name).alias('topic'))
    rows.append(hits)
h = pl.concat(rows)
h.write_parquet(T + 'topic_hits.parquet')
m = (h.with_columns(pl.col('time').dt.strftime('%Y-%m').alias('month'))
     .group_by('topic', 'src', 'month').len().sort('topic', 'month'))
m.write_csv(T + 'topic_monthly.csv')
pl.Config.set_tbl_rows(400); pl.Config.set_fmt_str_lengths(160); pl.Config.set_tbl_width_chars(250)
print(h.group_by('topic', 'src').len().pivot(on='src', index='topic', values='len').sort('topic'))
for name in TOPICS:
    x = h.filter(pl.col('topic') == name, pl.col('src') != 'memory').sort('time').head(4)
    print('==', name)
    for r in x.iter_rows(named=True):
        print(' ', r['time'], r['src'], r['agent'], '|', r['text'][:220].replace('\n', ' '))
