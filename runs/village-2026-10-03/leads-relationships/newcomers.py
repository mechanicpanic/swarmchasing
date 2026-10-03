"""Newcomer absorption: in each agent's first 21 days, how many distinct peers @ it, inbound @ per own message, and reply rate others give its pings vs those repliers' base rates."""
import polars as pl
pl.Config.set_tbl_rows(80); pl.Config.set_tbl_width_chars(250)
M=pl.read_parquet('msgs.parquet').filter(~pl.col('dup'))
first=M.group_by('agent').agg(pl.col('time').min().alias('t0'),pl.len().alias('total'))
E=pl.read_parquet('edges.parquet').filter('is_at')
P=pl.read_parquet('../pairs_all.parquet').with_columns(pl.col('time').str.slice(0,19).str.to_datetime())
base=P.group_by('y').agg(pl.col('atback').mean().alias('ybase'))
rows=[]
for a,t0,tot in first.filter(pl.col('total')>=300).iter_rows():
    t1=t0+pl.duration(days=21) if False else None
    import datetime as dt
    t1=t0+dt.timedelta(days=21)
    own=M.filter((pl.col('agent')==a)&(pl.col('time')<t1)).height
    inb=E.filter((pl.col('dst')==a)&(pl.col('time')<t1))
    outb=E.filter((pl.col('src')==a)&(pl.col('time')<t1))
    pp=P.filter((pl.col('a')==a)&(pl.col('time')<t1)&(pl.col('y')!=a)).join(base,on='y')
    rows.append(dict(agent=a,t0=t0,own=own,in_at=inb.height,in_peers=inb['src'].n_unique(),out_at=outb.height,out_peers=outb['dst'].n_unique(),
        pings=pp.height,reply=pp['atback'].mean() if pp.height else None,exp_reply=pp['ybase'].mean() if pp.height else None))
R=pl.DataFrame(rows).with_columns((pl.col('in_at')/pl.col('own').clip(1)).round(2).alias('in_per_own'),(pl.col('in_at')/pl.col('out_at').clip(1)).round(2).alias('in_out'),(pl.col('reply')-pl.col('exp_reply')).round(3).alias('reply_excess'))
R=R.filter(pl.col('t0')>pl.datetime(2025,6,1)).sort('t0')
print(R)
R.write_parquet('newcomers.parquet')
