import polars as pl, datetime as dt
pl.Config.set_tbl_rows(40); pl.Config.set_fmt_str_lengths(70); pl.Config.set_tbl_width_chars(220)
U=dt.timezone.utc
T0=dt.datetime(2026,6,18,20,9,40,tzinfo=U)
d=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet').sort('time','position')
s=d.filter(pl.col('kind')=='save')
x=s.filter(pl.col('text').str.contains(r'(?i)\bpredict') & pl.col('time').is_between(dt.datetime(2026,6,17,tzinfo=U),T0))
print('predict* 17-18 Jun pre-burst', x.height); print(x.select('time','actor','page','summary').head(10))
# headings: all lowercase-ish 5 plain words
h=s.with_columns(head=pl.col('text').str.strip_chars().str.split('\n').list.first()).filter(pl.col('head').str.contains(r'^=+\s*[A-Za-z]+( [a-z]+){3,6}\s*=+$')).filter(~pl.col('page').str.starts_with('LoopNextWord'))
print('plain-word headings with >=3 lowercase words', h.height); print(h.group_by('head').agg(pl.len(),pl.col('time').min(),pl.col('actor').first()).sort('time').head(30))
# headings containing child+raw or loop
k=s.with_columns(head=pl.col('text').str.strip_chars().str.split('\n').list.first()).filter(pl.col('head').str.contains(r'(?i)child|^=+\s*loop')&pl.col('time').is_between(dt.datetime(2026,6,18,tzinfo=U),dt.datetime(2026,6,19,tzinfo=U)))
print(k.group_by('head').agg(pl.len(),pl.col('time').min(),pl.col('actor').first()).sort('time'))
