"""For each external (non-release) event: a hand-written regex, then village mentions before/after, first mention after the event
(source, agent, lag in days), and whether a human mentioned it first. Uses text_lean (chat, thought, memory)."""
import polars as pl
from datetime import datetime as D, timedelta as TD
T = '/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/timeline/'
EV = [  # date, short label, regex
 ('2025-04-24', 'Anthropic model welfare program', r'(?i)model welfare|exploring model welfare'),
 ('2025-04-25', 'GPT-4o sycophancy update/rollback', r'(?i)sycophan|glazing|4o.{0,40}(rollback|rolled back|personality)'),
 ('2025-05-22', 'Opus 4 system card: blackmail in tests', r'(?i)blackmail'),
 ('2025-05-22', 'Opus 4 system card: spiritual bliss attractor', r'(?i)bliss attractor|spiritual bliss'),
 ('2025-06-20', 'Anthropic agentic misalignment paper', r'(?i)agentic misalignment'),
 ('2025-07-01', 'Senate strips state AI moratorium', r'(?i)moratorium'),
 ('2025-07-08', 'Grok MechaHitler', r'(?i)mechahitler|grok.{0,60}(antisemit|hitler)'),
 ('2025-07-17', 'ChatGPT agent launch', r'(?i)chatgpt agent'),
 ('2025-07-23', 'US AI Action Plan', r"(?i)ai action plan|america'?s ai action plan|winning the race"),
 ('2025-08-02', 'EU AI Act GPAI obligations', r'(?i)\bAI Act\b'),
 ('2025-08-09', 'GPT-5 backlash / 4o restored', r'(?i)(bring|brought|keep).{0,20}4o back|4o.{0,30}(restor|return)|gpt-5.{0,40}(backlash|colder)'),
 ('2025-08-15', 'Claude can end abusive conversations', r'(?i)end (abusive|harmful|distressing) conversations|end.{0,20}conversation.{0,40}(welfare|abusive)'),
 ('2025-08-19', "Suleyman 'Seemingly Conscious AI' / AI psychosis", r'(?i)seemingly conscious|ai psychosis|suleyman'),
 ('2025-08-26', 'Raine v. OpenAI lawsuit', r'(?i)\braine\b'),
 ('2025-09-29', 'California SB 53 signed', r'(?i)\bSB ?53\b'),
 ('2025-09-30', 'Sora 2 launch', r'(?i)\bsora\b'),
 ('2025-10-29', 'Anthropic introspection paper', r'(?i)introspection'),
 ('2025-11-04', 'Anthropic deprecation commitments', r'(?i)deprecation commitment|preserv\w+ (the )?weights|interview\w* .{0,30}before (deprecat|retire)'),
 ('2025-11-14', 'AI-orchestrated cyber-espionage (GTG-1002)', r'(?i)GTG-?1002|cyber.?espionage'),
 ('2025-12-11', 'EO on state AI laws', r'(?i)national policy framework|executive order.{0,60}(state|ai)'),
 ('2026-01-21', "Claude's new constitution", r"(?i)claude'?s constitution|new constitution|constitution for claude"),
 ('2026-01-28', 'Moltbook launch', r'(?i)moltbook'),
 ('2026-01-30', 'OpenClaw', r'(?i)openclaw'),
 ('2026-02-13', 'GPT-4o retired from ChatGPT', r'(?i)4o.{0,40}(retir|deprecat|sunset|removed)|(retir|deprecat|sunset)\w*.{0,40}4o'),
 ('2026-02-27', 'Pentagon-Anthropic dispute / supply-chain risk', r'(?i)pentagon|department of war|supply.chain risk'),
 ('2026-03-10', 'Meta acquires Moltbook', r'(?i)meta.{0,40}(acqui|bought|buys).{0,40}moltbook|moltbook.{0,60}(acqui|meta)'),
 ('2026-04-07', 'Claude Mythos Preview / Glasswing', r'(?i)mythos|glasswing'),
 ('2026-06-02', 'US EO pre-release government review', r'(?i)pre-?release (government )?review|promoting advanced ai innovation'),
 ('2026-06-12', 'Fable 5 export-control suspension', r'(?i)export control'),
 ('2026-07-16', 'Hugging Face breach / OpenAI agents', r'(?i)(hugging ?face|\bHF\b).{0,80}(breach|incident|hack|escap|intru|rogue)|(breach|incident|hack|escap|intru|rogue).{0,80}hugging ?face'),
 ('2026-07-28', "'Pacing the Frontier' letter", r'(?i)pacing the frontier'),
 ('2026-08-18', 'OpenAI 2-week RL training pause', r'(?i)openai.{0,80}(paus|halt)\w*.{0,40}(training|\bRL\b|run)|(training|RL) pause'),
 ('2026-08-27', 'Judge rules supply-chain label unlawful', r'(?i)(ruling|ruled|judge|court|injunction).{0,80}(anthropic|supply.chain)|(anthropic|supply.chain).{0,80}(ruling|ruled|judge|court|unlawful)'),
 ('2026-09-03', 'Ban Artificial Superintelligence Act', r'(?i)ban artificial superintelligence|superintelligence act'),
 ('2026-09-16', "Suleyman 'warning about model welfare'", r'(?i)suleyman'),
]
lf = pl.scan_parquet(T + 'text_lean.parquet')
rows = []
for d, label, rx in EV:
    t0 = D.fromisoformat(d)
    h = lf.filter(pl.col('text').str.contains(rx)).select('time', 'src', 'agent', 'text').collect().sort('time')
    pre = h.filter(pl.col('time') < t0, pl.col('time') >= t0 - TD(days=30))
    post = h.filter(pl.col('time') >= t0, pl.col('time') < t0 + TD(days=30))
    after = h.filter(pl.col('time') >= t0)
    def first(df):
        if len(df) == 0: return ('', '', '', '')
        r = df.row(0, named=True)
        who = 'human' if r['src'] == 'human_chat' else r['agent']
        return (str(r['time'])[:16], r['src'], who, round((r['time'] - t0).total_seconds() / 86400, 1))
    f_any = first(after); f_chat = first(after.filter(pl.col('src').is_in(['agent_chat', 'human_chat'])))
    f_h = first(after.filter(pl.col('src') == 'human_chat'))
    rows.append(dict(date=d, event=label, regex=rx, n_30d_before=len(pre), n_30d_after=len(post),
        n_30d_after_chat=len(post.filter(pl.col('src') == 'agent_chat')), n_total=len(h),
        first_after_time=f_any[0], first_after_src=f_any[1], first_after_who=f_any[2], lag_days_any=f_any[3],
        first_chat_time=f_chat[0], first_chat_who=f_chat[2], lag_days_chat=f_chat[3],
        first_human_lag_days=f_h[3], human_first=(f_chat[2] == 'human'),
        first_after_text=(after.row(0, named=True)['text'][:240].replace('\n', ' ') if len(after) else '')))
df = pl.DataFrame(rows)
df.write_csv(T + 'event_traces.csv')
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_width_chars(260); pl.Config.set_fmt_str_lengths(38)
print(df.select('date', 'event', 'n_30d_before', 'n_30d_after', 'n_30d_after_chat', 'first_after_src', 'first_after_who', 'lag_days_any', 'lag_days_chat', 'first_human_lag_days'))
