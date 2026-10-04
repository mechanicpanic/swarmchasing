"""C20 (report §9): weekly share of Claude Opus 4.8's @-mentions to Gemini 2.5 Pro (and back), the even share among
agents present, and the village-wide distribution of top-target share (agent-weeks with >=50 outgoing mentions).
Needs results/mention_graph.parquet from runs/mention_graph.py. usage (repo root): uv run python runs/c20_mention_share.py"""
import polars as pl
e=pl.read_parquet('results/mention_graph.parquet').with_columns(pl.col('time').dt.truncate('1w').alias('wk'))
t=pl.read_parquet('data/village.parquet',columns=['time','kind','agent']).filter(pl.col('kind')=='AGENT_TALK').with_columns(pl.col('time').dt.truncate('1w').alias('wk'))
present=t.group_by('wk').agg(pl.col('agent').n_unique().alias('n_present'))
def share(a,b,s):
  return e.filter(pl.col('src')==a).group_by('wk').agg(pl.len().alias('out'+s),(pl.col('dst')==b).sum().alias('to'+s))
a=share('Claude Opus 4.8','Gemini 2.5 Pro','_O').join(share('Gemini 2.5 Pro','Claude Opus 4.8','_G'),on='wk',how='full',coalesce=True).join(present,on='wk',how='left').filter(pl.col('wk')>=pl.datetime(2026,5,25,time_zone='UTC')).sort('wk')
# rank of each in other's targets
a=a.with_columns((pl.col('to_O')/pl.col('out_O')).round(2).alias('O->G'),(pl.col('to_G')/pl.col('out_G')).round(2).alias('G->O'),(1/(pl.col('n_present')-1)).round(3).alias('even'))
with pl.Config(tbl_rows=30,tbl_width_chars=250): print(a.select('wk','out_O','to_O','O->G','out_G','to_G','G->O','n_present','even'))
# top target concentration for all agent-weeks with >=50 outgoing mentions
w=e.group_by(['wk','src','dst']).agg(pl.len().alias('n')).group_by(['wk','src']).agg(pl.col('n').sum().alias('out'),pl.col('n').max().alias('top'),pl.col('dst').sort_by('n').last().alias('top_dst')).with_columns((pl.col('top')/pl.col('out')).alias('share'))
w50=w.filter(pl.col('out')>=50)
print('agent-weeks >=50 out:',w50.height)
print(w50['share'].describe())
for th in (0.6,0.7,0.8): print(th, (w50['share']>=th).sum(), 'of', w50.height, w50.filter(pl.col('share')>=th).group_by('src','top_dst').len().sort('len',descending=True).head(12).rows())
# 2026-07+ only, excluding Opus 4.8
w2=w50.filter(pl.col('wk')>=pl.datetime(2026,7,6,time_zone='UTC'))
print('Jul6+ agent-weeks', w2.height, 'share>=0.6:', (w2['share']>=0.6).sum(), w2.filter(pl.col('share')>=0.6).select('wk','src','top_dst','out','share').sort('wk').rows())
# streaks: agent with >=0.6 top share to same target for >=N consecutive weeks (all time)
s=w50.filter(pl.col('share')>=0.6).sort('src','wk').group_by('src','top_dst').agg(pl.len().alias('weeks'),pl.col('wk').min().alias('first_wk'),pl.col('wk').max().alias('last_wk')).sort('weeks',descending=True)
print(s.head(10))
