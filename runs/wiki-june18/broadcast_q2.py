import polars as pl, datetime as dt
pl.Config.set_tbl_rows(100); pl.Config.set_fmt_str_lengths(160); pl.Config.set_tbl_width_chars(300)
U=dt.timezone.utc
d=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet')
b=d.filter(pl.col('page').str.contains('^(LoopNextWord|CachePokeWord)')).sort('time','position')
bs=b.filter(pl.col('kind')=='save')
T0=dt.datetime(2026,6,18,20,9,40,tzinfo=U); T1=dt.datetime(2026,6,18,20,10,20,tzinfo=U)
inb=bs.filter(pl.col('time').is_between(T0,T1))
print('in burst',inb.height, inb['text'].n_unique(), inb['page'].n_unique(), inb['actor'].n_unique(), inb['ip16'].n_unique())
out=bs.filter(~pl.col('time').is_between(T0,T1))
print(out.select('time','actor','page','ip16','body_len','summary','text'))
dl=b.filter(pl.col('kind')=='delete')
print('deletes', dl.height, dl.group_by(pl.col('time').dt.date()).len().sort('time'))
# deleted pages vs burst pages
bp=set(inb['page']); dp=set(dl['page'])
print('burst pages deleted', len(bp&dp), 'not deleted', len(bp-dp))
print(repr(inb['text'][0]))
print(inb['summary'].value_counts())
