"""C33: do labels with the same task-clock date relay to each other more than to other dates?
Shapes: "c27" = C27's relay pairs (same text_key added by label A on page P, FOLLOWED_BY the same text_key added by
another label on another page within 10 min; runs/c27_relay/c27.py, inline on wiki_msgs); "any<W>" = a wider
sensitivity: every ordered pair of adds of one text_key by different labels on different pages within W (10m, 1h,
1d, all). C27's exclusions (B, R, U; +J, +W). Unit: distinct (source save, destination save). Labels get a date
tag from dates.py. Statistic: same-date pairs among dated-dated pairs. Nulls permute date tags among the dated
labels active in the same UTC day ("day") or hour ("hour"); each end of a pair takes the tag of its own stratum.
Who relays to whom, when and where stays fixed; only which date a label carries moves.
usage (repo root): REPO=<main checkout> OUT=<json> python runs/c33_date_cohorts/c33.py [N]"""
import json, os, re, sys
from collections import Counter
from datetime import datetime
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path[:0] = [str(HERE), str(HERE.parent / 'c27_relay')]
import c27  # noqa: E402
from dates import parse  # noqa: E402

URL = re.compile(r'(?i)https?://|www\.|\b[\w-]+\.(com|gov|org|net|md|io|edu)\b')
WINDOWS = {'any10m': 600, 'any1h': 3600, 'any1d': 86400, 'anyall': 10 ** 9}


def keep(s, e, combo, unpub):
    drop = {'B': e['text_key'] in c27.BROADCAST, 'R': bool(c27.REDIR_ANY.match(e['text'])),
            'U': s['rev'] in unpub or e['rev'] in unpub, 'J': '2026-06-18' in (s['day'], e['day']),
            'W': c27.HUB in (s['page'], e['page'])}
    return not any(drop[x] for x in combo)


def units(matches, combo, unpub):
    """distinct (source save, destination save); link = the jumping text contains a URL or a domain."""
    out = {}
    for s, e in matches:
        if keep(s, e, combo, unpub):
            out.setdefault((s['rev'], e['rev']), (s, e, bool(URL.search(e['text']))))
    return list(out.values())


def wide(docs, window):
    ts = lambda d: datetime.fromisoformat(d['time'].replace('Z', '+00:00')).timestamp()  # noqa: E731
    by = {}
    for d in docs:
        if d['kind'] == 'add' and d['text_key'] and d['text_key'] not in c27.BROADCAST:
            by.setdefault(d['text_key'], []).append((ts(d), d))
    out = []
    for rows in by.values():
        rows.sort(key=lambda r: r[0])
        for i, (ti, s) in enumerate(rows):
            for tj, e in rows[i + 1:]:
                if tj - ti > window: break
                if e['label'] != s['label'] and e['page'] != s['page']: out.append((s, e))
    return out


class Nulls:
    """(stratum, label) slots of dated labels; one null draw = a permutation of tags within each stratum."""
    def __init__(self, docs, tag, kind):
        self.kind, cut = kind, 10 if kind == 'day' else 13
        slots = sorted({(d['time'][:cut], d['label']) for d in docs if tag.get(d['label'])})
        self.idx = {s: i for i, s in enumerate(slots)}
        self.grp = np.unique([s for s, _ in slots], return_inverse=True)[1]
        self.tags = np.array([tag[lab] for _, lab in slots])

    def ends(self, pairs):
        cut = 10 if self.kind == 'day' else 13
        return (np.array([self.idx[(s['time'][:cut], s['label'])] for s, e, _ in pairs], dtype=int),
                np.array([self.idx[(e['time'][:cut], e['label'])] for s, e, _ in pairs], dtype=int))

    def draw(self, rng):
        # slots are sorted by stratum, so a stratum-major order with random ties is a within-stratum permutation
        return self.tags[np.lexsort((rng.random(len(self.tags)), self.grp))]


def analyse(pairs, tag, nulls, n, rng):
    dd = [p for p in pairs if tag[p[0]['label']] and tag[p[1]['label']]]
    same = [p for p in dd if tag[p[0]['label']] == tag[p[1]['label']]]
    lp = lambda ps: len({frozenset((s['label'], e['label'])) for s, e, _ in ps})  # noqa: E731
    r = {'pairs': len(pairs), 'dated_dated': len(dd), 'same': len(same), 'same_labelpairs': lp(same),
         'one_dated': sum(bool(tag[s['label']]) != bool(tag[e['label']]) for s, e, _ in pairs),
         'per_date': dict(Counter(tag[s['label']] for s, _, _ in same)), 'null': {}}
    for k, nu in nulls.items():
        a, b = nu.ends(dd); xs = np.zeros(n, int); pd = Counter()
        for i in range(n):
            t = nu.draw(rng); hit = t[a] == t[b]; xs[i] = hit.sum(); pd.update(t[a][hit].tolist())
        xs.sort()
        r['null'][k] = {'mean': float(xs.mean()), 'p95': int(xs[int(0.95 * n) - 1]), 'max': int(xs[-1]),
                        'p': float(((xs >= len(same)).sum() + 1) / (n + 1)),
                        'per_date_mean': {d: v / n for d, v in pd.items() if d in r['per_date'] or v / n >= 0.5}}
    return r


def main(n):
    docs, unpub = c27.load()
    tag = {lab: parse(lab)[0] for lab in {d['label'] for d in docs}}
    m27 = c27.run(docs)
    print('C27 matches (expect 641):', len(m27), flush=True)
    nulls = {k: Nulls(docs, tag, k) for k in ('day', 'hour')}
    rng = np.random.default_rng(33); res = {}; ex = []
    shapes = {'c27': m27, **{w: wide(docs, s) for w, s in WINDOWS.items()}}
    for shape, matches in shapes.items():
        for combo in ['BRU', 'BRUJ', 'BRUW']:
            allp = units(matches, combo, unpub)
            for sub, ps in [('all', allp), ('nolink', [p for p in allp if not p[2]])]:
                r = res[f'{shape}/{combo}/{sub}'] = analyse(ps, tag, nulls, n, rng)
                nd, nh = r['null']['day'], r['null']['hour']
                print(f"{shape:6s} {combo:5s} {sub:6s} pairs {r['pairs']:5d} dd {r['dated_dated']:4d} same "
                      f"{r['same']:3d} ({r['same'] / max(r['dated_dated'], 1):5.1%}) lp {r['same_labelpairs']:3d} | "
                      f"day {nd['mean']:6.1f}/{nd['p95']:3d} p={nd['p']:.4f} | hour {nh['mean']:6.1f}/{nh['p95']:3d} "
                      f"p={nh['p']:.4f}", flush=True)
            if combo == 'BRU' and shape in ('c27', 'any1d'):
                ex += [{'shape': shape, 'src': s['id'], 'dst': e['id'], 'labels': [s['label'], e['label']],
                        'date': tag[s['label']], 'pages': [s['page'], e['page']], 'times': [s['time'], e['time']],
                        'link': lk, 'text': e['text'][:240]}
                       for s, e, lk in allp if tag[s['label']] and tag[s['label']] == tag[e['label']]]
    json.dump({'n': n, 'results': res, 'same_date_pairs': ex},
              open(os.environ.get('OUT', HERE / 'c33_out.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2000)
