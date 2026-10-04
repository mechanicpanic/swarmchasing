import os
OUT = os.environ.get('OUT', '../../results/c17')
import re, polars as pl, numpy as np, datetime as _d
from dicts import peers_in, SENT, SUSP_CORE
HON = [w for w in SUSP_CORE if not w.startswith('suspect') and not w.startswith('suspicion')]
R = r"(?i)\b(" + "|".join(HON) + r")\b"; rr = re.compile(R)
T = pl.read_parquet(f'{OUT}/T.parquet')
def sp(text, me): return any(rr.search(s) and peers_in(s, me) for s in SENT.findall(text))
T = T.with_columns(h=pl.col('text').str.contains(R))
T = T.with_columns(hp=pl.struct('text','agent','h').map_elements(lambda x: x['h'] and sp(x['text'], x['agent']), return_dtype=pl.Boolean))
T = T.with_columns(hps=pl.col('hp') & ~pl.col('game'))
d = T.group_by('day').agg(pl.len().alias('nT'), pl.col('h').sum(), pl.col('hp').sum(), pl.col('hps').sum()).sort('day'); days = d['day'].to_list()
g0 = days.index(_d.date(2026,3,5)); gend = days.index(_d.date(2026,3,16)); W=7
for c in ['h','hp','hps']:
    rate = (d[c]*1000/d['nT']).to_numpy(); x = rate[g0:g0+W].mean()
    plac = np.array([rate[s:s+W].mean() for s in range(len(days)-W+1) if s+W-1 < g0 or s > gend])
    print(c, round(x,2), f"rank {1+(plac>=x).sum()}/{len(plac)+1}", 'median', round(np.median(plac),2), 'p95', round(np.quantile(plac,.95),2), 'n_game', int(d[c][g0:g0+W].sum()), 'n_out', int(d[c].sum()-d[c][g0:gend+1].sum()))
print(d[g0:g0+7].select('day','hp','hps'))
ing = (pl.col('day') >= _d.date(2026,3,5)) & (pl.col('day') <= _d.date(2026,3,16))
for x in T.filter(~ing & pl.col('hp')).sort('day').iter_rows(named=True):
    s=[s for s in SENT.findall(x['text']) if rr.search(s) and peers_in(s,x['agent'])][0]
    print(x['id'][:8], x['day'], x['agent'][:14], '|', s[:200].replace('\n',' '))
