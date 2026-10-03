import polars as pl
pl.Config.set_tbl_rows(80); pl.Config.set_tbl_width_chars(250)
V=pl.read_parquet('verify.parquet')
E=pl.read_parquet('edges.parquet')
rec=E.group_by('dst').agg(pl.len().alias('mentions_in'))
v=V.group_by('x').agg(pl.len().alias('verified'),pl.col('refute').sum().alias('refuted')).join(rec,left_on='x',right_on='dst')
v=v.with_columns((pl.col('verified')*1000/pl.col('mentions_in')).alias('verif_per1k_mentions'),(pl.col('refuted')/pl.col('verified')).alias('refute_share')).filter(pl.col('mentions_in')>=1000)
print(v.sort('verif_per1k_mentions',descending=True))
# GPT-5.2 over time vs others: windows
def win(t):
    return (pl.when(t<pl.datetime(2026,3,5)).then(pl.lit('a_pre_game')).when(t<pl.datetime(2026,3,12,20,54)).then(pl.lit('b_game_pre397'))
      .when(t<pl.datetime(2026,3,17)).then(pl.lit('c_game_post397')).when(t<pl.datetime(2026,5,1)).then(pl.lit('d_mar17_apr')).otherwise(pl.lit('e_may+')))
Vw=V.filter(pl.col('time')>pl.datetime(2025,12,1)).with_columns(win(pl.col('time')).alias('w'))
Ew=E.filter(pl.col('time')>pl.datetime(2025,12,1)).with_columns(win(pl.col('time')).alias('w'))
a=Vw.group_by('x','w').agg(pl.len().alias('ver'),pl.col('refute').sum().alias('ref'))
b=Ew.group_by(pl.col('dst').alias('x'),'w').agg(pl.len().alias('men'))
t=b.join(a,on=['x','w'],how='left').fill_null(0).with_columns((pl.col('ver')*1000/pl.col('men')).round(1).alias('ver_per1k'),(pl.col('ref')*1000/pl.col('men')).round(1).alias('ref_per1k'))
print(t.filter(pl.col('x').is_in(['GPT-5.2','GPT-5.1','DeepSeek-V3.2','Claude Opus 4.5','Claude Opus 4.6','Gemini 3.1 Pro','Claude Haiku 4.5','Gemini 2.5 Pro','Claude Sonnet 4.6'])).sort('x','w'))
# corrections received by GPT-5.2 over windows
R=pl.read_parquet('../conflicts/corrections.parquet').with_columns(pl.col('time').str.to_datetime()).filter(pl.col('time')>pl.datetime(2025,12,1)).with_columns(win(pl.col('time')).alias('w'))
c=R.group_by(pl.col('b').alias('x'),'w').agg(pl.len().alias('corr_in'))
t2=b.join(c,on=['x','w'],how='left').fill_null(0).with_columns((pl.col('corr_in')*1000/pl.col('men')).round(1).alias('corr_per1k'))
print(t2.filter(pl.col('x').is_in(['GPT-5.2','GPT-5.1','DeepSeek-V3.2','Claude Opus 4.5','Gemini 3.1 Pro','Claude Haiku 4.5'])).sort('x','w'))
