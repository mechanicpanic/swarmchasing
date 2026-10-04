"""Rupture->repair: weeks where a pair has a burst of corrections (corrections.parquet, both directions), then track share-of-mentions after."""
import polars as pl
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_width_chars(250)
U=pl.read_parquet('undirected_weekly.parquet').sort('p1','p2','week')
W=pl.read_parquet('pair_weekly.parquet').with_columns(pl.min_horizontal('src','dst').alias('p1'),pl.max_horizontal('src','dst').alias('p2'))
c=W.group_by('p1','p2','week').agg((pl.col('corr_n').sum()+pl.col('contra_n').sum()).alias('cc'),pl.col('verify_refute_n').sum().alias('vref'))
U=U.join(c,on=['p1','p2','week'],how='left').fill_null(0)
# all weeks grid per pair so gaps count as zeros; use r only where cop
U=U.with_columns(pl.when(pl.col('cop')).then(pl.col('r')).otherwise(None).alias('rc'))
for k,(a,b) in {'pre':(-4,-1),'dip':(1,2),'rec':(3,6)}.items():
    U=U.with_columns(pl.mean_horizontal([pl.col('rc').shift(-i).over('p1','p2') for i in range(a,b+1)]).alias(k))
B=U.filter((pl.col('cc')>=4)).with_columns((pl.col('cc')/pl.col('m').clip(1)).alias('cc_share'))
B=B.with_columns(((pl.col('week')>=pl.datetime(2026,3,2))&(pl.col('week')<=pl.datetime(2026,3,16))).alias('saboteur'))
B=B.with_columns((pl.col('dip')/pl.col('pre')).alias('dip_ratio'),(pl.col('rec')/pl.col('pre')).alias('rec_ratio'))
print(B.select('p1','p2','week','m','cc','vref','pre','dip','rec','dip_ratio','rec_ratio','saboteur').sort('cc',descending=True).head(40))
print('rupture->repair candidates')
print(B.filter((pl.col('dip_ratio')<0.6)&(pl.col('rec_ratio')>0.8)).select('p1','p2','week','m','cc','pre','dip','rec','saboteur'))
B.write_parquet('rupture_candidates.parquet')
