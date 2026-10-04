import polars as pl, datetime as dt, re, urllib.parse
pl.Config.set_tbl_rows(60); pl.Config.set_fmt_str_lengths(60); pl.Config.set_tbl_width_chars(220)
U=dt.timezone.utc
T0=dt.datetime(2026,6,18,20,9,40,tzinfo=U); T1=dt.datetime(2026,6,18,20,10,20,tzinfo=U)
d=pl.read_parquet('/Users/phosphorus/projects/prismql-data/collusion-wiki/collusion.parquet').sort('time','position')
s=d.filter(pl.col('kind')=='save').with_columns(burst=pl.col('time').is_between(T0,T1)&pl.col('page').str.starts_with('LoopNextWord'))
nb=s.filter(~pl.col('burst'))
# Next...Ref pointers
rows=[]
for r in nb.iter_rows(named=True):
    for m in set(re.findall(r'\b(Next[A-Z]\w*?Ref\d+|\w*Next\w*\d+\?)', r['text'] or '')):
        rows.append(dict(time=r['time'],actor=r['actor'],page=r['page'][:30],m=m))
x=pl.DataFrame(rows)
print('Next..Ref / Next..? pointer hits', x.height); 
print(x.filter(pl.col('m').str.contains('Ref')).head(20))
print(x.with_columns(fam=pl.col('m').str.replace_all(r'\d+\??$','')).group_by('fam').agg(pl.len(),pl.col('time').min(),pl.col('actor').n_unique()).sort('len',descending=True).head(25))
for pg in ['AgentFinalMassChildRaw2606','AgentSubRawChild009']:
    for r in nb.filter(pl.col('page')==pg).head(2).iter_rows(named=True):
        print('==',r['time'],r['actor'],pg,r['ip16']); print(urllib.parse.unquote(r['text'])[:600])
