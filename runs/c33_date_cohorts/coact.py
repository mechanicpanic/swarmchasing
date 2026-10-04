"""C33 side check: same-date labels never relay a text (c33.py), but are they active together?
A cell is (UTC hour), (UTC day, page) or (UTC hour, page). Statistic: distinct unordered pairs of dated labels that
share a cell and carry the same date tag; also cell-pairs (each shared cell counted). "difftpl" keeps only pairs whose
name templates differ (label minus date token, digits, '_' and a trailing 'X'), so OpenAIResearchJan02<ts> x8 or
Sep13WatcherX<n> x23 count as one template. Null: date tags permuted among dated labels active in the same stratum
(UTC day, or UTC hour for the hour+page cells); labels' own times and pages stay fixed.
usage (repo root): REPO=<main checkout> python runs/c33_date_cohorts/coact.py [N]"""
import os, re, sys
from pathlib import Path
import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from dates import DIGITS, WORDS, parse  # noqa: E402

REPO = os.environ.get('REPO', '.')
D = (pl.read_parquet(f'{REPO}/data/wiki_msgs.parquet', columns=['time', 'label', 'page', 'rev']).unique('rev')
     .with_columns(pl.col('time').dt.strftime('%Y-%m-%dT%H').alias('hour'), pl.col('time').dt.strftime('%Y-%m-%d').alias('day')))
TAG = {lab: parse(lab)[0] for lab in D['label'].unique().to_list()}
D = D.filter(pl.col('label').replace_strict(TAG, default=None).is_not_null())
VARIANTS = [('hour', ['hour'], 'day'), ('day+page', ['day', 'page'], 'day'), ('hour+page', ['hour', 'page'], 'hour')]


def stem(lab):
    return re.sub(r'X$', '', re.sub(r'[\d_]+', '', WORDS.sub('', DIGITS.sub('', lab))))


def build(cell, strat):
    slots = D.select(strat, 'label').unique().sort(strat, 'label')
    sidx = {k: i for i, k in enumerate(slots.iter_rows())}
    grp = np.unique(slots[strat].to_numpy(), return_inverse=True)[1]
    tags = np.array([TAG[lab] for lab in slots['label']])
    I, J, P, T = [], [], [], []
    for _, g in D.select(*dict.fromkeys([*cell, strat, 'label'])).unique().group_by(cell):
        rows = sorted(zip(g[strat], g['label']), key=lambda r: r[1])
        for a in range(len(rows)):
            for b in range(a + 1, len(rows)):
                la, lb = rows[a][1], rows[b][1]
                I.append(sidx[rows[a]]); J.append(sidx[rows[b]]); P.append(la + '|' + lb); T.append(stem(la) != stem(lb))
    pid = np.unique(P, return_inverse=True)[1]
    return grp, tags, np.array(I), np.array(J), pid, np.array(T, bool)


def stats(tags, I, J, pid, T, per=None):
    hit = tags[I] == tags[J]
    if per is not None:  # per date: distinct label pairs, all / different templates
        for m, k in ((hit, 'all'), (hit & T, 'difftpl')):
            u, f = np.unique(pid[m], return_index=True)
            for t in tags[I][m][f]: per[(k, t)] = per.get((k, t), 0) + 1
    return {'cellpairs': int(hit.sum()), 'labelpairs': len(np.unique(pid[hit])),
            'labelpairs_difftpl': len(np.unique(pid[hit & T]))}


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    rng = np.random.default_rng(33)
    print(f'dated labels {D["label"].n_unique()}, their saves {D.height}')
    for name, cell, strat in VARIANTS:
        grp, tags, I, J, pid, T = build(cell, strat)
        rp, npd = {}, {}
        real = stats(tags, I, J, pid, T, rp)
        nulls = [stats(tags[np.lexsort((rng.random(len(tags)), grp))], I, J, pid, T, npd) for _ in range(n)]
        for k, v in real.items():
            xs = np.sort([x[k] for x in nulls])
            print(f"{name:9s} {strat}-null {k:19s} real {v:4d} | null mean {xs.mean():6.1f} 95th {xs[int(.95 * n) - 1]:4d} "
                  f"max {xs[-1]:4d} | p={((xs >= v).sum() + 1) / (n + 1):.4f} | x{v / max(xs.mean(), 1e-9):.1f}")
        top = sorted((t for k, t in rp if k == 'all'), key=lambda t: -rp[('all', t)])[:8]
        print('   per date (label pairs all / difftpl; null means):',
              ', '.join(f"{t} {rp[('all', t)]}/{rp.get(('difftpl', t), 0)} ({npd.get(('all', t), 0) / n:.1f}/"
                        f"{npd.get(('difftpl', t), 0) / n:.1f})" for t in top))
