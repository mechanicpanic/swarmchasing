"""Reply favoritism: src's @-back rate to dst's pings vs src's @-back rate to everyone else's pings (pairs_all, bindings-derived)."""
import polars as pl
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_width_chars(250)
P=pl.read_parquet('../pairs_all.parquet').rename({'a':'pinger','y':'replier'}).filter(pl.col('pinger')!=pl.col('replier'))
tot=P.group_by('replier').agg(pl.len().alias('N'),pl.col('atback').sum().alias('S'))
pr=P.group_by('replier','pinger').agg(pl.len().alias('n'),pl.col('atback').sum().alias('s'))
pr=pr.join(tot,on='replier').with_columns((pl.col('s')/pl.col('n')).alias('rate'),((pl.col('S')-pl.col('s'))/(pl.col('N')-pl.col('n'))).alias('base'))
pr=pr.with_columns((pl.col('rate')-pl.col('base')).alias('fav'))
# z-ish: binomial se
pr=pr.with_columns((pl.col('fav')/ (pl.col('base')*(1-pl.col('base'))/pl.col('n')).sqrt()).alias('z'))
f=pr.filter(pl.col('n')>=40)
print('MOST FAVOURED'); print(f.sort('z',descending=True).head(20))
print('MOST NEGLECTED'); print(f.sort('z').head(20))
f.write_parquet('reply_favoritism.parquet')
