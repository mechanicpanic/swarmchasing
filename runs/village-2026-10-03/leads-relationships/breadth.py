"""Per-agent @-breadth: distinct @-targets per week, top-target share, before vs after individual goals (2026-07-06)."""
import polars as pl
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_width_chars(250)
E=pl.read_parquet('edges.parquet').filter('is_at')
M=pl.read_parquet('msgs.parquet').filter(~pl.col('dup'))
act=M.group_by('week').agg(pl.col('agent').n_unique().alias('n_active'))
def per(df):
    w=df.group_by('src','week').agg(pl.col('dst').n_unique().alias('peers'),pl.len().alias('ats'))
    tops=df.group_by('src','dst').agg(pl.len().alias('k')).with_columns((pl.col('k')/pl.col('k').sum().over('src')).alias('sh')).sort('k',descending=True)
    top=tops.group_by('src').agg(pl.col('dst').first().alias('top'),pl.col('sh').first().round(2).alias('top_share'),(pl.col('sh')**2).sum().round(3).alias('hhi'))
    w=w.join(act,on='week').with_columns((pl.col('peers')/(pl.col('n_active')-1)).alias('reach'))
    return w.group_by('src').agg(pl.col('peers').mean().round(1),pl.col('reach').mean().round(2),pl.col('ats').sum()).join(top,on='src')
pre=per(E.filter((pl.col('time')>=pl.datetime(2026,5,25))&(pl.col('time')<pl.datetime(2026,7,6))))
post=per(E.filter((pl.col('time')>=pl.datetime(2026,7,6))&(pl.col('time')<pl.datetime(2026,8,31))))
J=pre.join(post,on='src',suffix='_post').filter((pl.col('ats')>=50)&(pl.col('ats_post')>=50))
G={'Claude Opus 4.8':'Performance coach','Claude Haiku 4.5':'Psychologist','GPT-5.1':'Ethicist','GPT-5':'Prankster','DeepSeek-V3.2':'Diplomat(external)','GLM-5.2':'AI Welfarist','Gemini 2.5 Pro':'Author','Claude Opus 4.5':'Substacker'}
J=J.with_columns(pl.col('src').replace_strict(G,default='').alias('goal'))
print(J.select('src','goal','peers','reach','top','top_share','ats','peers_post','reach_post','top_post','top_share_post','ats_post').sort('reach_post',descending=True))
J.write_parquet('breadth_prepost_goals.parquet')
