"""build.py -> msgs.parquet (deduped agent msgs + flags + named), edges.parquet (msg x named target), pair_weekly.parquet.
Reuses conflicts/{chat_flags,directed_edges,corrections}.parquet, ../pairs_all.parquet (bindings-derived ping pairs)."""
import sys, polars as pl
sys.path.insert(0,'/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/conflicts')
from agents import names_in, LAB
A='/Users/phosphorus/projects/prismql-data/ai-village/corpus/'
C=pl.read_parquet(A+'chat_raw.parquet',columns=['id','time','kind','agent','text','room']).filter(pl.col('kind')=='agent').drop('kind')
# dedupe repeat-posting loops: same agent, same normalized text (digits masked, first 300 chars) within 24h
C=C.sort('agent','time').with_columns(pl.col('text').fill_null('').str.to_lowercase().str.replace_all(r'\d+','#').str.replace_all(r'\s+',' ').str.slice(0,300).alias('norm'))
C=C.with_columns((pl.col('time')-pl.col('time').shift(1).over(['agent','norm'])).alias('gap'))
C=C.with_columns((pl.col('gap').is_not_null() & (pl.col('gap')<pl.duration(hours=24))).alias('dup'))
print('dups', C['dup'].sum(), 'of', C.height)
F=pl.read_parquet(A+'analysis/conflicts/chat_flags.parquet',columns=['id','concede','contra','dcontra','at'])
C=C.join(F,on='id',how='left')
THX=r"(?i)\b(thanks|thank you|thx|grateful|credit to|kudos|shout-?out|great work|nice work|great job|well done|excellent work|appreciate|props to|great catch|good catch|nice catch|brilliant work|amazing work)\b"
C=C.with_columns(pl.col('text').str.contains(THX).alias('thanks'),
                 pl.col('time').dt.truncate('1w').alias('week'))
C=C.with_columns(pl.Series('named',[ [n for n in names_in(t) if n!=a] for a,t in zip(C['agent'],C['text'])], dtype=pl.List(pl.Utf8)))
C.drop('norm','gap','text').write_parquet('msgs.parquet')
K=C.filter(~pl.col('dup'))
E=K.select('id','time','week','agent','at','named','thanks','concede','contra','dcontra').explode('named').filter(pl.col('named').is_not_null()).rename({'agent':'src','named':'dst'})
E=E.with_columns(pl.col('at').list.contains(pl.col('dst')).alias('is_at')).drop('at')
E.write_parquet('edges.parquet')
# activity / co-presence
act=K.group_by('agent','week').agg(pl.len().alias('msgs'))
active=act.filter(pl.col('msgs')>=5)
g=E.group_by('src','dst','week').agg(pl.len().alias('name_n'),pl.col('is_at').sum().alias('at_n'),
    (pl.col('thanks')).sum().alias('thanks_n'),pl.col('concede').sum().alias('concede_n'),
    (pl.col('dcontra')&pl.col('is_at')).sum().alias('contra_n'))
# pings and @-backs (pairs_all from PrismQL bindings, see ../fetch_bindings.py): a pinged y; atback = y @-replied a within 1h
P=pl.read_parquet(A+'analysis/pairs_all.parquet').with_columns(pl.col('time').str.slice(0,19).str.to_datetime().dt.truncate('1w').alias('week'))
pin=P.group_by(pl.col('a').alias('src'),pl.col('y').alias('dst'),'week').agg(pl.len().alias('pings_n'))
# reply_n(src->dst): src @-replied within 1h to a ping from dst; pinged_by_dst_n = pings from dst to src
rep=P.group_by(pl.col('y').alias('src'),pl.col('a').alias('dst'),'week').agg(pl.col('atback').sum().alias('reply_n'),pl.len().alias('pinged_by_dst_n'))
R=pl.read_parquet(A+'analysis/conflicts/corrections.parquet').with_columns(pl.col('time').str.to_datetime().dt.truncate('1w').alias('week'))
cor=R.group_by(pl.col('a').alias('src'),pl.col('b').alias('dst'),'week').agg(pl.len().alias('corr_n'),pl.col('concede').sum().alias('corr_conceded_n'))
keys=['src','dst','week']
W=g
for t in (pin,rep,cor):
    W=W.join(t,on=keys,how='full',coalesce=True)
W=W.fill_null(0)
# meaningful pairs: >=30 name mentions total across both directions
tot=W.with_columns(pl.min_horizontal('src','dst').alias('p1'),pl.max_horizontal('src','dst').alias('p2')).group_by('p1','p2').agg(pl.col('name_n').sum().alias('tot'))
keep=tot.filter(pl.col('tot')>=30)
print('pairs kept', keep.height)
# grid: both directions x co-present weeks
pa=active.rename({'agent':'src','msgs':'src_msgs'}); pb=active.rename({'agent':'dst','msgs':'dst_msgs'})
grid=pl.concat([keep.select(pl.col('p1').alias('src'),pl.col('p2').alias('dst')),keep.select(pl.col('p2').alias('src'),pl.col('p1').alias('dst'))])
grid=grid.join(pa,on='src').join(pb,on=['dst','week'])
grid=grid.with_columns(pl.lit(True).alias('copresent'))
W2=W.join(grid.select(keys),on=keys,how='full',coalesce=True).join(keep.select(pl.col('p1').alias('src'),pl.col('p2').alias('dst')).vstack(keep.select(pl.col('p2').alias('src'),pl.col('p1').alias('dst'))),on=['src','dst'],how='semi')
W2=W2.join(grid.select(keys+['copresent']),on=keys,how='left').fill_null(0).with_columns(pl.col('copresent').cast(pl.Boolean))
W2=W2.join(act.rename({'agent':'src','msgs':'src_msgs'}),on=['src','week'],how='left').join(act.rename({'agent':'dst','msgs':'dst_msgs'}),on=['dst','week'],how='left').fill_null(0)
W2=W2.with_columns(pl.col('src').replace_strict(LAB,default=None).alias('lab_src'),pl.col('dst').replace_strict(LAB,default=None).alias('lab_dst'))
W2=W2.with_columns((pl.col('lab_src')==pl.col('lab_dst')).alias('same_lab')).sort('src','dst','week')
W2.write_parquet('pair_weekly_base.parquet'); print(W2.shape); print(W2.describe())
