import polars as pl
pl.Config.set_tbl_rows(80); pl.Config.set_tbl_width_chars(250); pl.Config.set_fmt_str_lengths(40)
E=pl.read_parquet('edges.parquet')
out=E.group_by('src','week').agg(pl.len().alias('out_all'))
W=pl.read_parquet('pair_weekly.parquet').join(out,on=['src','week'],how='left').fill_null(0)
W=W.with_columns(pl.min_horizontal('src','dst').alias('p1'),pl.max_horizontal('src','dst').alias('p2'))
U=W.group_by('p1','p2','week').agg(pl.col('name_n').sum().alias('m'),pl.col('out_all').sum().alias('den'),pl.col('copresent').all().alias('cop'),
   pl.col('corr_n').sum().alias('corr'),pl.col('thanks_n').sum().alias('thx'),pl.col('concede_n').sum().alias('conc')).sort('p1','p2','week')
U=U.with_columns((pl.col('m')/pl.col('den').clip(1)).alias('r'))
U.write_parquet('undirected_weekly.parquet')
print(U.group_by('p1','p2').agg(pl.col('m').sum()).sort('m',descending=True).head(25))
# change score: 3 co-present weeks before vs 3 after
RC=pl.read_parquet('pair_weekly.parquet').filter('room_copresent').select(pl.min_horizontal('src','dst').alias('p1'),pl.max_horizontal('src','dst').alias('p2'),'week').unique(); U=U.join(RC,on=['p1','p2','week'],how='semi').filter('cop')
U=U.with_columns(pl.col('m').rolling_sum(3).over('p1','p2').alias('m_b3'),pl.col('den').rolling_sum(3).over('p1','p2').alias('d_b3'),
                 pl.col('week').shift(3).over('p1','p2').alias('w_b3'))
U=U.with_columns(pl.col('m_b3').shift(-3).over('p1','p2').alias('m_a3'),pl.col('d_b3').shift(-3).over('p1','p2').alias('d_a3'),pl.col('week').shift(-3).over('p1','p2').alias('w_a3'))
U=U.with_columns(((pl.col('m_a3')+2)/(pl.col('d_a3')+20)).alias('ra'),((pl.col('m_b3')+2)/(pl.col('d_b3')+20)).alias('rb'))
U=U.with_columns((pl.col('ra')/pl.col('rb')).log(2).alias('lfc'),
                 ((pl.col('w_a3')-pl.col('w_b3')).dt.total_days()).alias('span'))
U=U.filter(pl.col('span')<=49)
cols=['p1','p2','week','m_b3','d_b3','m_a3','d_a3','lfc']
warm=U.filter((pl.col('m_a3')>=25)).sort('lfc',descending=True).unique(['p1','p2'],keep='first').sort('lfc',descending=True)
print('WARM'); print(warm.select(cols).head(30))
cool=U.filter((pl.col('m_b3')>=25)).sort('lfc').unique(['p1','p2'],keep='first').sort('lfc')
print('COOL'); print(cool.select(cols).head(30))
warm.select(cols).write_parquet('warm_room.parquet'); cool.select(cols).write_parquet('cool_room.parquet')
