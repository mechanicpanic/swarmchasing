"""show.py A B START END [N] [regex]: messages by A naming B or B naming A in [START,END), evenly sampled."""
import sys, polars as pl
A='/Users/phosphorus/projects/prismql-data/ai-village/corpus/'
a,b,s,e=sys.argv[1:5]; n=int(sys.argv[5]) if len(sys.argv)>5 else 12; rx=sys.argv[6] if len(sys.argv)>6 else None
E=pl.read_parquet('edges.parquet',columns=['id','src','dst','time']).filter(((pl.col('src')==a)&(pl.col('dst')==b))|((pl.col('src')==b)&(pl.col('dst')==a)))
E=E.filter((pl.col('time')>=pl.lit(s).str.to_datetime())&(pl.col('time')<pl.lit(e).str.to_datetime())).unique('id').sort('time')
C=pl.read_parquet(A+'chat_raw.parquet',columns=['id','text','room'])
E=E.join(C,on='id').sort('time')
if rx: E=E.filter(pl.col('text').str.contains(rx))
print('n=',E.height)
step=max(1,E.height//n)
for r in E[::step].head(n).iter_rows(named=True):
    print(f"[{str(r['time'])[:16]} {r['room']}] {r['src']}: {r['text'][:260]!r}\n")
