import os
OUT = os.environ.get('OUT', '../../results/c17')
import polars as pl, numpy as np, datetime as _d
T = pl.read_parquet(f'{OUT}/T.parquet'); M = pl.read_parquet(f'{OUT}/M.parquet')
T = T.with_columns(strict=pl.col('core_peer') & ~pl.col('game'))
M = M.with_columns(contra_code=pl.col('contra') & pl.col('control_m'), conc_code=pl.col('conc') & pl.col('control_m'))
dt = T.group_by('day').agg(pl.len().alias('nT'), pl.col('strict').sum(), pl.col('core_peer').sum(), pl.col('control').sum())
dm = M.group_by('day').agg(pl.len().alias('nM'), pl.col('contra').sum(), pl.col('conc').sum(), pl.col('dcontra').sum(), pl.col('control_m').sum(), pl.col('contra_code').sum(), pl.col('conc_code').sum())
d = dt.join(dm, on='day').sort('day'); days = d['day'].to_list()
g0 = days.index(_d.date(2026,3,5)); gend = days.index(_d.date(2026,3,16)); W = 7
def stat(num, den, start=g0, name=None):
    rate = (d[num]*1000/d[den]).to_numpy(); x = rate[start:start+W].mean()
    plac = np.array([rate[s:s+W].mean() for s in range(len(days)-W+1) if s+W-1 < g0 or s > gend])
    return dict(stat=name or f'{num}/{den}', win=str(days[start]), value=round(x,2), rank=f"{1+(plac>=x).sum()}/{len(plac)+1}",
                median=round(np.median(plac),2), p95=round(np.quantile(plac,.95),2), n=int(d[num][start:start+W].sum()))
pl.Config.set_tbl_width_chars(200); pl.Config.set_tbl_cols(20)
post = days.index(_d.date(2026,3,17))
rows = [stat('strict','nT'), stat('contra','control_m', name='contra per 1k code msgs'), stat('conc','control_m', name='conc per 1k code msgs'),
        stat('dcontra','control_m', name='dcontra per 1k code msgs'),
        stat('core_peer','nT',post,'core_peer post-game'), stat('contra','nM',post,'contra post-game'), stat('conc','nM',post,'conc post-game'),
        stat('dcontra','nM',post,'dcontra post-game'), stat('control','nT',post,'control post-game')]
print(pl.DataFrame(rows))
# without the two last game days (vote/reveal climax): first 5 game days vs 5-day placebo
def stat5(num, den, W=5):
    rate = (d[num]*1000/d[den]).to_numpy(); x = rate[g0:g0+W].mean()
    plac = np.array([rate[s:s+W].mean() for s in range(len(days)-W+1) if s+W-1 < g0 or s > gend])
    return dict(stat=num+' first5', value=round(x,2), rank=f"{1+(plac>=x).sum()}/{len(plac)+1}", median=round(np.median(plac),2), p95=round(np.quantile(plac,.95),2))
print(pl.DataFrame([stat5('core_peer','nT'), stat5('strict','nT'), stat5('contra','nM'), stat5('dcontra','nM'), stat5('conc','nM'), stat5('control','nT')]))
# per-day share of in-game counts
g = d[g0:g0+7].select('day','strict','core_peer','contra','dcontra','conc')
print(g)
