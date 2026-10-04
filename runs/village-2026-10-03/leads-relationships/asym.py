import polars as pl
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_width_chars(250)
W=pl.read_parquet('pair_weekly.parquet')
ab=W.group_by('src','dst').agg(pl.col('at_n').sum().alias('at_ab'),pl.col('name_n').sum().alias('nm_ab'),pl.col('pings_n').sum().alias('ping_ab'),
   pl.col('reply_n').sum().alias('rep_ab'),pl.col('pinged_by_dst_n').sum().alias('pinged_ab'),pl.col('thanks_n').sum().alias('thx_ab'))
ba=ab.rename({c:c.replace('_ab','_ba') for c in ab.columns if c.endswith('_ab')}).rename({'src':'dst','dst':'src'})
J=ab.join(ba,on=['src','dst']).filter(pl.col('src')<pl.col('dst'))
J=J.with_columns(((pl.col('nm_ab')-pl.col('nm_ba'))/(pl.col('nm_ab')+pl.col('nm_ba'))).alias('asym_name'),
   (pl.col('rep_ab')/pl.col('pinged_ab')).alias('src_replies_rate'),(pl.col('rep_ba')/pl.col('pinged_ba')).alias('dst_replies_rate'))
J=J.filter((pl.col('nm_ab')+pl.col('nm_ba'))>=150)
print(J.sort(pl.col('asym_name').abs(),descending=True).select('src','dst','nm_ab','nm_ba','asym_name','ping_ab','ping_ba','src_replies_rate','dst_replies_rate').head(30))
# reply-rate asymmetry: who answers whose pings
J2=J.filter((pl.col('pinged_ab')>=40)&(pl.col('pinged_ba')>=40)).with_columns((pl.col('src_replies_rate')-pl.col('dst_replies_rate')).alias('rdiff'))
print(J2.sort(pl.col('rdiff').abs(),descending=True).select('src','dst','ping_ab','ping_ba','src_replies_rate','dst_replies_rate','rdiff').head(25))
# flips: monthly asymmetry sign change
M=W.with_columns(pl.col('week').dt.truncate('1mo').alias('mo')).group_by('src','dst','mo').agg(pl.col('name_n').sum())
M2=M.join(M.rename({'src':'dst','dst':'src','name_n':'nm_ba'}),on=['src','dst','mo'],how='full',coalesce=True).fill_null(0).filter(pl.col('src')<pl.col('dst'))
M2=M2.filter((pl.col('name_n')+pl.col('nm_ba'))>=40).with_columns(((pl.col('name_n')-pl.col('nm_ba'))/(pl.col('name_n')+pl.col('nm_ba'))).alias('a')).sort('src','dst','mo')
fl=M2.group_by('src','dst').agg(pl.col('a').max().alias('amax'),pl.col('a').min().alias('amin'),pl.col('mo').filter(pl.col('a')==pl.col('a').max()).first().alias('mo_max'),pl.col('mo').filter(pl.col('a')==pl.col('a').min()).first().alias('mo_min'),pl.len().alias('months'))
fl=fl.filter((pl.col('amax')>0.4)&(pl.col('amin')<-0.4)).with_columns((pl.col('amax')-pl.col('amin')).alias('swing')).sort('swing',descending=True)
print(fl.head(25))
J.write_parquet('asym_pairs.parquet'); fl.write_parquet('asym_flips.parquet'); M2.write_parquet('pair_monthly_asym.parquet')
