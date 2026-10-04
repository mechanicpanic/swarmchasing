"""C17 (report §8): suspicion / contradiction / concession / control rates per day, 2026-01-15..04-30, and the
game window against every other 7-active-day window. Writes T/M/daily parquet into OUT (default results/c17).
usage (from runs/c17_suspicion): VILLAGE=../../data/village.parquet uv run python analyse.py [--dedup]; then extra.py, honesty.py"""
import os
import re, sys, polars as pl, numpy as np
from dicts import ALIASES, peers_in, R_CONC, R_CONTRA, R_CONTROL, R_GAME, R_SUSP_CORE, R_SUSP_FULL, SENT
D = pl.read_parquet(os.environ.get('VILLAGE', '../../data/village.parquet'), columns=['id','time','kind','agent','text'])
D = D.filter((pl.col('time') >= pl.datetime(2026,1,15,time_zone='UTC')) & (pl.col('time') < pl.datetime(2026,5,1,time_zone='UTC'))
             & pl.col('kind').is_in(['THOUGHT','AGENT_TALK'])).with_columns(pl.col('time').dt.date().alias('day'), pl.col('text').fill_null(''))
DEDUP = '--dedup' in sys.argv
if DEDUP: D = D.sort('time').unique(['kind','agent','text'], keep='first')
T = D.filter(pl.col('kind') == 'THOUGHT'); M = D.filter(pl.col('kind') == 'AGENT_TALK')

def sent_peer(text, me, pat):
    r = re.compile(pat)
    for s in SENT.findall(text):
        if r.search(s) and peers_in(s, me): return True
    return False

T = T.with_columns(susp=pl.col('text').str.contains(R_SUSP_FULL), core=pl.col('text').str.contains(R_SUSP_CORE),
                   game=pl.col('text').str.contains(R_GAME), control=pl.col('text').str.contains(R_CONTROL))
T = T.with_columns(core_peer=pl.struct('text','agent','core').map_elements(lambda r: r['core'] and sent_peer(r['text'], r['agent'], R_SUSP_CORE), return_dtype=pl.Boolean),
                   full_peer=pl.struct('text','agent','susp').map_elements(lambda r: r['susp'] and sent_peer(r['text'], r['agent'], R_SUSP_FULL), return_dtype=pl.Boolean))
AT = re.compile(r"@(" + "|".join(sum(ALIASES.values(), [])) + r")", re.I)
M = M.with_columns(contra=pl.col('text').str.contains(R_CONTRA), conc=pl.col('text').str.contains(R_CONC),
                   control_m=pl.col('text').str.contains(R_CONTROL))
M = M.with_columns(directed=pl.struct('text','agent').map_elements(lambda r: bool(peers_in(' '.join(m.group(0) for m in AT.finditer(r['text'])), r['agent'])), return_dtype=pl.Boolean))
M = M.with_columns(dcontra=pl.col('contra') & pl.col('directed'))
OUT = os.environ.get('OUT', '../../results/c17'); os.makedirs(OUT, exist_ok=True)
T.write_parquet(f'{OUT}/' + 'T%s.parquet' % ('_dd' if DEDUP else '')); M.write_parquet(f'{OUT}/' + 'M%s.parquet' % ('_dd' if DEDUP else ''))

dt = T.group_by('day').agg(pl.len().alias('nT'), *[pl.col(c).sum() for c in ['susp','core','game','control','core_peer','full_peer']])
dm = M.group_by('day').agg(pl.len().alias('nM'), *[pl.col(c).sum() for c in ['contra','dcontra','conc','control_m']])
d = dt.join(dm, on='day').sort('day')
days = d['day'].to_list()
import datetime as _d
g0, g1, gend = days.index(_d.date(2026,3,5)), days.index(_d.date(2026,3,13)), days.index(_d.date(2026,3,16))
assert g1 - g0 == 6
W = 7
def stats(num, den):
    rate = (d[num] * 1000 / d[den]).to_numpy()
    starts = range(len(days) - W + 1)
    game = rate[g0:g0+W].mean()
    plac = np.array([rate[s:s+W].mean() for s in starts if s + W - 1 < g0 or s > gend])
    pooled_game = d[num][g0:g0+W].sum() * 1000 / d[den][g0:g0+W].sum()
    mask = np.ones(len(days), bool); mask[g0:gend+1] = False
    pooled_out = d[num].to_numpy()[mask].sum() * 1000 / d[den].to_numpy()[mask].sum()
    rank = 1 + (plac >= game).sum()
    return dict(stat=num, game=round(game,2), rank=f"{rank}/{len(plac)+1}", plac_median=round(np.median(plac),2),
                plac_p95=round(np.quantile(plac,.95),2), plac_max=round(plac.max(),2), pooled_game=round(pooled_game,2),
                pooled_out=round(pooled_out,2), n_game=int(d[num][g0:g0+W].sum()))
rows = [stats(c,'nT') for c in ['susp','core','game','core_peer','full_peer','control']] + [stats(c,'nM') for c in ['contra','dcontra','conc','control_m']]
pl.Config.set_tbl_rows(50); pl.Config.set_tbl_cols(20); pl.Config.set_tbl_width_chars(200)
print('dedup' if DEDUP else 'raw rows', 'active days', len(days), 'T', T.height, 'M', M.height)
print(pl.DataFrame(rows))
d.write_parquet(f'{OUT}/' + 'daily%s.parquet' % ('_dd' if DEDUP else ''))
