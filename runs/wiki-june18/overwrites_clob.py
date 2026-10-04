import pickle,datetime as dt
revs=pickle.load(open('dse_revs.pkl','rb'))
WITH='[pre-2026 line withheld]'; TPL={'Beschreibe hier die neue Seite.','Describe the new page here.'}
def T(s): return dt.datetime.fromisoformat(s.replace('Z','+00:00'))
ev=[]
for name,rs in revs.items():
    rs=sorted(rs,key=lambda r:r['seq'])
    for p,r in zip(rs,rs[1:]):
        if r['label']==p['label'] or 'Admin' in (r['label'] or '') or 'Admin' in (p['label'] or ''): continue
        pa=[x for x in p['body'].split('\n') if x.strip() and x!=WITH and x.strip() not in TPL]
        if len(pa)<1: continue
        s=set(r['body'].split('\n'))
        lost=sum(1 for x in pa if x not in s)
        gap=(T(r['time'])-T(p['time'])).total_seconds()
        ev.append(dict(page=name,time=r['time'],by=r['label'],victim=p['label'],n=len(pa),lost=lost,gap=gap,summ=r['change_summary']))
import polars as pl
d=pl.DataFrame(ev).with_columns(pl.col('time').str.to_datetime(time_zone='UTC'))
d.write_parquet('pairs.parquet')
c=d.filter((pl.col('lost')/pl.col('n')>=0.5)&(pl.col('gap')<=600))
print('other-label consecutive saves',len(d),' clobbers(>=50% lost, <=10min)',len(c))
print(c.with_columns(pl.col('time').dt.date().alias('day')).group_by('day').len().sort('day'))
print(c.group_by('page').len().sort('len',descending=True).head(15))
pl.Config.set_tbl_rows(40); pl.Config.set_fmt_str_lengths(60); pl.Config.set_tbl_width_chars(250)
print(c.sort('time').head(40))
