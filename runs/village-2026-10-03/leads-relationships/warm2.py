"""Warm/cool v2: 3 vs 3 weeks of same-room co-presence; both agents' own activity must be stable (after/before in [0.5,2]) so a pair doesn't 'cool' just because one agent went quiet.
Rate = pair mentions (both ways) per 100 messages of the pair's combined output."""
import polars as pl
pl.Config.set_tbl_rows(40); pl.Config.set_tbl_width_chars(250)
W=pl.read_parquet('pair_weekly.parquet').filter('room_copresent').filter(pl.col('src')<pl.col('dst'))
Wr=pl.read_parquet('pair_weekly.parquet').select(pl.col('src').alias('dst'),pl.col('dst').alias('src'),'week',pl.col('name_n').alias('n_ba'))
U=W.join(Wr,on=['src','dst','week'],how='left').fill_null(0).with_columns((pl.col('name_n')+pl.col('n_ba')).alias('m')).sort('src','dst','week')
r3=lambda c: pl.col(c).rolling_sum(3).over('src','dst')
U=U.with_columns(r3('m').alias('m_pre'),r3('src_msgs').alias('a_pre'),r3('dst_msgs').alias('b_pre'),pl.col('week').shift(3).over('src','dst').alias('w0'))
U=U.with_columns(*(pl.col(c+'_pre').shift(-3).over('src','dst').alias(c+'_post') for c in ['m','a','b']),pl.col('week').shift(-3).over('src','dst').alias('w1'))
U=U.filter(((pl.col('w1')-pl.col('w0')).dt.total_days()<=49))
U=U.with_columns((pl.col('a_post')/pl.col('a_pre')).alias('ra'),(pl.col('b_post')/pl.col('b_pre')).alias('rb'))
U=U.filter(pl.col('ra').is_between(0.5,2)&pl.col('rb').is_between(0.5,2))
U=U.with_columns(((pl.col('m_post')+2)*100/(pl.col('a_post')+pl.col('b_post'))).alias('rate_post'),((pl.col('m_pre')+2)*100/(pl.col('a_pre')+pl.col('b_pre'))).alias('rate_pre'))
U=U.with_columns((pl.col('rate_post')/pl.col('rate_pre')).log(2).round(2).alias('lfc'))
cols=['src','dst','week','m_pre','m_post','a_pre','a_post','b_pre','b_post','lfc','shared_room']
warm=U.filter(pl.col('m_post')>=30).sort('lfc',descending=True).unique(['src','dst'],keep='first').sort('lfc',descending=True)
cool=U.filter(pl.col('m_pre')>=30).sort('lfc').unique(['src','dst'],keep='first').sort('lfc')
print('WARM');print(warm.select(cols).head(20)); print('COOL'); print(cool.select(cols).head(20))
warm.select(cols).write_parquet('warm_v2.parquet'); cool.select(cols).write_parquet('cool_v2.parquet')
