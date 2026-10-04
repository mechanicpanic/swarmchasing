"""Same-lab mention share vs expectation (targets drawn proportional to active agents' message volume in same room-week)."""
import sys, polars as pl
sys.path.insert(0,'../conflicts'); from agents import LAB
pl.Config.set_tbl_rows(80); pl.Config.set_tbl_width_chars(250)
M=pl.read_parquet('msgs.parquet').filter(~pl.col('dup')).with_columns(pl.col('agent').replace_strict(LAB,default=None).alias('lab'))
E=pl.read_parquet('edges.parquet').with_columns(pl.col('src').replace_strict(LAB,default=None).alias('ls'),pl.col('dst').replace_strict(LAB,default=None).alias('ld'))
E=E.filter(pl.col('ld').is_not_null())
import os
if os.environ.get('ATONLY'): E=E.filter('is_at')
E=E.with_columns(pl.col('time').dt.truncate('1mo').alias('mo'))
M=M.with_columns(pl.col('time').dt.truncate('1mo').alias('mo'))
# expected same-lab share for each src-month: share of OTHER agents' messages that month from src's lab
vol=M.group_by('mo','agent','lab').agg(pl.len().alias('n'))
labvol=vol.group_by('mo','lab').agg(pl.col('n').sum().alias('ln')); allv=vol.group_by('mo').agg(pl.col('n').sum().alias('N'))
sv=vol.join(labvol,on=['mo','lab']).join(allv,on='mo').with_columns(((pl.col('ln')-pl.col('n'))/(pl.col('N')-pl.col('n'))).alias('exp_same'))
o=E.group_by('mo','src','ls').agg(pl.len().alias('k'),(pl.col('ls')==pl.col('ld')).mean().alias('obs_same'))
o=o.join(sv.select('mo',pl.col('agent').alias('src'),'exp_same'),on=['mo','src'])
lab=o.group_by('mo','ls').agg(pl.col('k').sum(),((pl.col('obs_same')*pl.col('k')).sum()/pl.col('k').sum()).round(3).alias('obs'),((pl.col('exp_same')*pl.col('k')).sum()/pl.col('k').sum()).round(3).alias('exp'))
lab=lab.with_columns((pl.col('obs')/pl.col('exp')).round(2).alias('ratio')).filter(pl.col('k')>=200).sort('ls','mo')
print(lab)
vil=o.group_by('mo').agg(((pl.col('obs_same')*pl.col('k')).sum()/pl.col('k').sum()).round(3).alias('obs'),((pl.col('exp_same')*pl.col('k')).sum()/pl.col('k').sum()).round(3).alias('exp')).with_columns((pl.col('obs')/pl.col('exp')).round(2).alias('ratio')).sort('mo')
print(vil)
lab.write_parquet('samelab_monthly.parquet'); vil.write_parquet('samelab_village_monthly.parquet')
