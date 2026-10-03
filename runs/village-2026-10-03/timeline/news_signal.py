"""Weekly 'outside AI-world news' signal: share of agent chat / thought rows that pair an AI lab or government actor with a news verb.
Also weekly volumes. Output: news_weekly.csv"""
import polars as pl
T = '/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/timeline/'
ACT = r"(openai|anthropic|google deepmind|deepmind|\bxai\b|meta ai|\bmeta\b|hugging ?face|deepseek|moonshot|zhipu|white house|congress|pentagon|department of war|\bEU\b|european commission|government|regulator|\bFTC\b|senate)"
VERB = r"(announc|releas|launch|disclos|lawsuit|sued|ruling|regulat|\bban(ned|s)?\b|incident|export control|executive order|\bdeal\b|contract|blacklist|designat|paus|suspend|breach|hack)"
RX = rf"(?i){ACT}.{{0,80}}{VERB}|{VERB}.{{0,80}}{ACT}"
lf = pl.scan_parquet(T + 'text_lean.parquet').filter(pl.col('src').is_in(['agent_chat', 'thought', 'human_chat']))
lf = lf.with_columns(pl.col('text').str.contains(RX).alias('news'))
wk = (lf.sort('time').group_by_dynamic('time', every='1w', group_by='src')
      .agg(pl.len().alias('n'), pl.col('news').sum().alias('news_n')).with_columns((pl.col('news_n') / pl.col('n')).alias('news_rate')).collect())
wk.write_csv(T + 'news_weekly.csv')
pl.Config.set_tbl_rows(200)
p = wk.pivot(on='src', index='time', values='news_rate').sort('time')
print(p.with_columns(pl.exclude('time').round(3)))
