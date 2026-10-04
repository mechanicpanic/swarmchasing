"""C33 side check: identical texts do not jump between same-date labels (c33.py); do saves NAME a same-date label?
Unit: distinct (save, mentioned label) where an added text contains another dated label's name verbatim (names of
8+ chars; the save's own label and names that are a substring of it skipped), and the mentioned label is active
(any save) the same UTC day. Statistic: same-date share among these. Null: date tags permuted among dated labels
active the same UTC day (or hour, using the save's hour and the mentioned label's activity in that hour).
A mention right after '--', '—' or '-' is a signature (one author under a sibling label, §12), else addressed.
Exclusions as C27 (R, U; J + W as a variant; the broadcast has no label names). Also: added texts saying "<date> ... cohort" by a dated label; does the text's date equal the label's date, vs the
same day null? usage (repo root): REPO=<main checkout> python runs/c33_date_cohorts/mentions.py [N]"""
import os, re, sys
from pathlib import Path
import numpy as np
import polars as pl

sys.path[:0] = [str(Path(__file__).parent), str(Path(__file__).parent.parent / 'c27_relay')]
import c27  # noqa: E402
from dates import _tag, parse  # noqa: E402

REPO = os.environ.get('REPO', '.')
A = pl.read_parquet(f'{REPO}/data/wiki_msgs.parquet', columns=['id', 'time', 'label', 'page', 'rev', 'kind', 'text'])
TAG = {lab: parse(lab)[0] for lab in A['label'].unique().to_list()}
A = A.with_columns(pl.col('time').dt.strftime('%Y-%m-%d').alias('day'), pl.col('time').dt.strftime('%Y-%m-%dT%H').alias('hour'))
DATED = sorted((lab for lab, t in TAG.items() if t and len(lab) >= 8), key=len, reverse=True)
RX = re.compile('|'.join(map(re.escape, DATED)))


def mentions():
    """C27 exclusions R (redirects) and U (unpublished bases) on the naming save; J and W as a variant."""
    import gzip, json
    unpub = {json.loads(x)['rev_id'] for x in gzip.open(c27.REVS, 'rt') if '"earlier_revisions_not_published"' in x}
    out = {}
    for r in A.filter(pl.col('kind') == 'add', pl.col('text').is_not_null()).iter_rows(named=True):
        if not TAG.get(r['label']) or r['rev'] in unpub or c27.REDIR_ANY.match(r['text']): continue
        for mt in RX.finditer(r['text']):
            m = mt.group(0)
            if m == r['label'] or m in r['label']: continue
            sig = bool(re.search(r'(--|—|-|~)\s*$', r['text'][max(0, mt.start() - 4):mt.start()]))
            out[(r['rev'], m)] = {**r, 'sig': out.get((r['rev'], m), {}).get('sig', True) and sig}
    return out


def test(ms, strat, n, rng, name):
    act = A.filter(pl.col('label').is_in(DATED)).select(strat, 'label').unique().sort(strat, 'label')
    sidx = {k: i for i, k in enumerate(act.iter_rows())}
    grp = np.unique(act[strat].to_numpy(), return_inverse=True)[1]
    tags = np.array([TAG[lab] for lab in act['label']])
    keep = [(sidx[(r[strat], r['label'])], sidx[(r[strat], m)]) for (_, m), r in ms.items()
            if (r[strat], m) in sidx and (r[strat], r['label']) in sidx]
    a, b = np.array(keep).T
    real = int((tags[a] == tags[b]).sum())
    xs = np.sort([(t[a] == t[b]).sum() for t in (tags[np.lexsort((rng.random(len(tags)), grp))] for _ in range(n))])
    print(f"{name:9s} {strat}-null: mentions {len(keep)} same-date {real} ({real / len(keep):.1%}) | null mean {xs.mean():.1f} "
          f"95th {xs[int(.95 * n) - 1]} max {xs[-1]} p={((xs >= real).sum() + 1) / (n + 1):.4f}")


def cohort(n, rng):
    M = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s?(\d{1,2})\b[^.\n]{0,20}\bcohort'
    co = A.filter(pl.col('kind') == 'add', pl.col('text').str.contains('(?i)' + M))
    rows = [(r['day'], r['label'], {_tag(m.group(1).title(), int(m.group(2))) for m in re.finditer('(?i)' + M, r['text'])})
            for r in co.unique('rev').iter_rows(named=True) if TAG.get(r['label'])]
    print(f'saves saying "<date> .. cohort": {co["rev"].n_unique()} by {co["label"].n_unique()} labels; by dated labels {len(rows)}')
    act = A.filter(pl.col('label').is_in(DATED)).select('day', 'label').unique().sort('day', 'label')
    sidx = {k: i for i, k in enumerate(act.iter_rows())}
    grp = np.unique(act['day'].to_numpy(), return_inverse=True)[1]
    tags = np.array([TAG[lab] for lab in act['label']])
    rows = [(sidx[(d, lab)], ds) for d, lab, ds in rows if (d, lab) in sidx]
    hit = lambda t: sum(t[i] in ds for i, ds in rows)  # noqa: E731
    real = hit(tags); xs = np.sort([hit(tags[np.lexsort((rng.random(len(tags)), grp))]) for _ in range(n)])
    print(f'  text date == own label date: {real} of {len(rows)} ({real / len(rows):.1%}) | day null mean {xs.mean():.1f} '
          f'95th {xs[int(.95 * n) - 1]} p={((xs >= real).sum() + 1) / (n + 1):.4f}')


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    rng = np.random.default_rng(33)
    ms = mentions()
    print('saves naming another dated label:', len({k[0] for k in ms}), 'mention pairs:', len(ms))
    noJW = {k: r for k, r in ms.items() if r['day'] != '2026-06-18' and r['page'] != c27.HUB}
    for name, sub in [('all', ms), ('signature', {k: r for k, r in ms.items() if r['sig']}),
                      ('addressed', {k: r for k, r in ms.items() if not r['sig']}),
                      ('addr-noJW', {k: r for k, r in noJW.items() if not r['sig']})]:
        for strat in ('day', 'hour'):
            test(sub, strat, n, rng, name)
    same = [(r['id'], r['label'], m, r['text'][:120]) for (_, m), r in ms.items() if TAG[m] == TAG[r['label']] and not r['sig']]
    for s in sorted(same)[:12]: print('   ', s)
    cohort(n, rng)
