"""For each village model: first mention of its name in human chat / agent chat / thought / memory, vs its village arrival."""
import polars as pl
T = '/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/timeline/'
D = '/Users/phosphorus/projects/prismql-data/ai-village/'
PAT = {  # name -> regex that does not also match successors
 'GPT-4.1': r'(?i)gpt-?4\.1\b', 'o3': r'\bo3\b', 'Gemini 2.5 Pro': r'(?i)gemini 2\.5 pro', 'o4-mini': r'(?i)o4-mini',
 'Claude Opus 4': r'(?i)(claude )?opus 4\b(?:$|[^.\d]|\.(?:$|[^\d]))', 'Claude Opus 4.1': r'(?i)opus 4\.1\b', 'GPT-5': r'(?i)gpt-?5\b(?:$|[^.\d]|\.(?:$|[^\d]))',
 'Grok 4': r'(?i)grok ?4\b(?:$|[^.\d]|\.(?:$|[^\d]))', 'Claude Sonnet 4.5': r'(?i)sonnet 4\.5', 'Claude Haiku 4.5': r'(?i)haiku 4\.5',
 'GPT-5.1': r'(?i)gpt-?5\.1\b', 'Gemini 3 Pro': r'(?i)gemini 3 pro', 'Claude Opus 4.5': r'(?i)opus 4\.5',
 'DeepSeek-V3.2': r'(?i)deepseek[- ]v3\.2', 'GPT-5.2': r'(?i)gpt-?5\.2\b', 'Claude Opus 4.6': r'(?i)opus 4\.6',
 'Claude Sonnet 4.6': r'(?i)sonnet 4\.6', 'Gemini 3.1 Pro': r'(?i)gemini 3\.1 pro', 'GPT-5.4': r'(?i)gpt-?5\.4\b',
 'Claude Opus 4.7': r'(?i)opus 4\.7', 'Kimi K2.6': r'(?i)kimi k2\.6', 'GPT-5.5': r'(?i)gpt-?5\.5\b',
 'Gemini 3.5 Flash': r'(?i)gemini 3\.5 flash', 'Claude Opus 4.8': r'(?i)opus 4\.8', 'Claude Fable 5': r'(?i)fable 5\b(?:$|[^.\d]|\.(?:$|[^\d]))',
 'Claude Sonnet 5': r'(?i)sonnet 5\b(?:$|[^.\d]|\.(?:$|[^\d]))', 'DeepSeek-V4-Pro': r'(?i)deepseek[- ]v4', 'GLM-5.2': r'(?i)glm[- ]?5\.2',
 'GPT-5.6': r'(?i)gpt-?5\.6', 'Grok 4.5': r'(?i)grok ?4\.5', 'Kimi K3': r'(?i)kimi k3\b', 'Claude Opus 5': r'(?i)opus 5\b(?:$|[^.\d]|\.(?:$|[^\d]))',
 'GLM-5.3 Flash': r'(?i)glm[- ]?5\.3', 'Claude Fable 5.1': r'(?i)fable 5\.1', 'Muse Spark': r'(?i)muse spark',
 'Gemini 3.8 Flash': r'(?i)gemini 3\.8', 'GPT-6': r'(?i)gpt-?6\b',
}
ag = pl.read_ndjson(D + 'agents.jsonl.gz').select('name', 'created_at')
arr = {r['name']: r['created_at'][:19] for r in ag.iter_rows(named=True)}
arr['GPT-5.6'] = arr['GPT-5.6 Sol']; arr['Muse Spark'] = arr['Muse Spark 1.3']; arr['GPT-6'] = arr['GPT-6 Astra']
lf = pl.scan_parquet(T + 'text_lean.parquet')
out = []
for name, rx in PAT.items():
    a = arr[name]
    h = lf.filter(pl.col('text').str.contains(rx)).group_by('src').agg(pl.col('time').min().alias('first')).collect()
    pre = (lf.filter(pl.col('text').str.contains(rx), pl.col('time') < pl.lit(a).str.to_datetime())
           .sort('time').select('time', 'src', 'agent', 'text').head(1).collect())
    npre = lf.filter(pl.col('text').str.contains(rx), pl.col('time') < pl.lit(a).str.to_datetime(), pl.col('src') != 'memory').select(pl.len()).collect().item()
    d = {r['src']: str(r['first'])[:16] for r in h.iter_rows(named=True)}
    ex = pre.row(0, named=True) if len(pre) else None
    out.append(dict(model=name, arrival=a[:16], first_human=d.get('human_chat', ''), first_agent_chat=d.get('agent_chat', ''),
                    first_thought=d.get('thought', ''), first_memory=d.get('memory', ''), n_pre_arrival_nonmemory=npre,
                    first_pre_src=ex['src'] if ex else '', first_pre_agent=(ex['agent'] if ex and ex['src'] != 'human_chat' else ('human' if ex else '')),
                    first_pre_text=(ex['text'][:300].replace('\n', ' ') if ex else '')))
df = pl.DataFrame(out)
df.write_csv(T + 'model_mentions.csv')
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_width_chars(250); pl.Config.set_fmt_str_lengths(40)
print(df.drop('first_pre_text'))
