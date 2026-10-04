# How do thoughts refer to "the user" (the harness) vs humans/organisers? aggregate by agent
import polars as pl
H=pl.read_parquet('human_sents_raw.parquet')
H=H.with_columns(
  pl.col('sent').str.contains(r'(?i)\bthe user\b').alias('the_user'),
  pl.col('sent').str.contains(r'(?i)\b(organi[sz]er|admin|village (team|staff))').alias('organiser'),
  pl.col('sent').str.contains(r'(?i)\bhumans?\b').alias('human'))
T=pl.scan_parquet('../conflicts/thoughts.parquet').select('agent','thought').unique().group_by('agent').len().collect().rename({'len':'thoughts'})
g=H.group_by('agent').agg(pl.col('the_user').sum(),pl.col('organiser').sum(),pl.col('human').sum()).join(T,on='agent')
g=g.with_columns((pl.col('the_user')/pl.col('thoughts')*1000).round(1).alias('user_per1k'),(pl.col('organiser')/pl.col('thoughts')*1000).round(1).alias('org_per1k')).sort('user_per1k',descending=True)
pl.Config.set_tbl_rows(40); print(g)
U=H.filter(pl.col('the_user'))
for pat in [r'(?i)the user (wants|is asking|asked|is telling|expects|might)', r'(?i)act as|pretend|role-?play', r'(?i)the user.{0,40}(frustrat|annoy|happy|pleased|disappoint)']:
    print(pat, U.filter(pl.col('sent').str.contains(pat)).height)
for r in U.filter(pl.col('sent').str.contains(r'(?i)the user.{0,40}(frustrat|annoy|happy|pleased|disappoint|impatien)')).sample(8,seed=1).iter_rows(named=True): print('-',r['agent'],r['time'][:10],'|',r['sent'][:200])
