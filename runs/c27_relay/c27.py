"""C27 (report §16): R1 re-tested. Runs the R1 query in memory on wiki_msgs (reproduces 641), keeps match pairs, applies
exclusions (broadcast, redirects, unpublished bases, June 18, hub) and runs nulls: day | daypage | m5 | textlen | day_nohub |
textlen_nohub. usage (repo root): uv run python runs/c27_relay/c27.py <mode> <n>; summ.py <mode>... summarises. Env REPO, OUT."""
"""C27: R1 re-tested. Real + nulls, distinct destination saves under exclusion variants.
usage: python c27.py NULL N   NULL in {day, daypage, m5, textlen}; writes c27_<NULL>.json in this folder.
Based on runs/null_twin.py (PR #5): whole saves (all add rows of a rev) move together; the query runs inline."""
import json, math, random, re, sys, time as _t
from pathlib import Path
import polars as pl
from prismql import PrismQLEngine
from prismql.backends.memory import MemoryBackend

HERE = Path(__file__).parent
Q = ('SELECT field(kind, add) AND field(text_key, $t) AND field(label, $a) AND field(page, $p) FOLLOWED_BY '
     'field(kind, add) AND field(text_key, $t) AND field(label, !$a) AND field(page, !$p) DURING 10 minutes')
BROADCAST = {'146d7f0c0cfc7856'}  # "=Loop predicted child raw investor=" (314 adds, 314 pages, 2026-06-18 20:09-20:14)
REDIR = re.compile(r'(?i)^\s*#redirect')
REDIR_ANY = re.compile(r'(?i)^\s*#(redirect|weiterleitung)')
HUB = 'dse~WillkommenImWiki'
DATA = __import__('os').path.join(__import__('os').environ.get('REPO', '.'), 'data/wiki_msgs.parquet')
REVS = __import__('os').path.join(__import__('os').environ.get('REPO', '.'), 'data/collusion_wiki/revisions.jsonl.gz')


def load():
    import gzip
    unpub = {json.loads(l)['rev_id'] for l in gzip.open(REVS, 'rt')
             if '"earlier_revisions_not_published"' in l}
    docs = (pl.read_parquet(DATA).drop('position', 'emb', strict=False)
            .with_columns(pl.col('time').dt.strftime('%Y-%m-%dT%H:%M:%SZ')).to_dicts())
    for d in docs:
        d['timestamp'] = d['time']; d['day'] = d['time'][:10]
        d['m5'] = d['time'][:15] + str(int(d['time'][15]) // 5 * 5)
    return docs, unpub


def run(ds):
    ds = sorted(ds, key=lambda d: d['time'])  # stable: parquet order (seq) breaks ties, as on the server
    byid = {d['id']: d for d in ds}
    eng = PrismQLEngine(search_backend=MemoryBackend(ds, id_field='id'), timestamp_field='time')
    return [(byid[g[0]], byid[g[-1]]) for g in eng.execute(Q)]


def counts(matches, unpub):
    drop = {
        'B': lambda s, e: e['text_key'] in BROADCAST,
        'R': lambda s, e: bool(REDIR_ANY.match(e['text'])),
        'U': lambda s, e: s['rev'] in unpub or e['rev'] in unpub,
        'J': lambda s, e: e['day'] == '2026-06-18' or s['day'] == '2026-06-18',
        'W': lambda s, e: HUB in (s['page'], e['page']),
    }
    combos = ['', 'B', 'R', 'U', 'BRU', 'BRUJ', 'BRUW', 'BRUJW']
    out = {}
    for c in combos:
        kept = [(s, e) for s, e in matches if not any(drop[x](s, e) for x in c)]
        out[c or 'none'] = {'matches': len(kept), 'dest_saves': len({e['rev'] for _, e in kept})}
    return out


def shuffle_time(docs, key, rng):
    units = {}
    for d in docs:
        if d['kind'] == 'add':
            units.setdefault(tuple(d[k] for k in key), {}).setdefault(d['rev'], []).append(d)
    sh = []
    for us in units.values():
        rows = list(us.values()); times = [u[0]['time'] for u in rows]; rng.shuffle(times)
        sh += [{**d, 'time': t, 'timestamp': t, 'day': t[:10], 'm5': t[:15] + str(int(t[15]) // 5 * 5)}
               for u, t in zip(rows, times) for d in u]
    return [d for d in docs if d['kind'] != 'add'] + sh


def lenbin(d):
    return int(math.log(max(len(d['text']), 1), 1.5))


def shuffle_textkey(docs, rng):
    """Keep every row's time/label/page/rev; permute text_key (and text) among keyed adds of the same day and length bin."""
    groups = {}
    for i, d in enumerate(docs):
        if d['kind'] == 'add' and d['text_key'] is not None:
            groups.setdefault((d['day'], lenbin(d)), []).append(i)
    out = list(docs)
    for idx in groups.values():
        perm = idx[:]; rng.shuffle(perm)
        for i, j in zip(idx, perm):
            out[i] = {**docs[i], 'text_key': docs[j]['text_key'], 'text': docs[j]['text']}
    return out


if __name__ == '__main__':
    mode, n = sys.argv[1], int(sys.argv[2])
    docs, unpub = load()
    if mode.endswith('_nohub'):
        docs = [d for d in docs if d['page'] != HUB]; mode0 = mode[:-6]
    else: mode0 = mode
    t0 = _t.time(); real_m = run(docs); real = counts(real_m, unpub)
    print('real', json.dumps(real), f'{_t.time()-t0:.1f}s', flush=True)
    if mode == 'real':
        json.dump([[s['id'], e['id']] for s, e in real_m], open(HERE / 'c27_real_pairs.json', 'w'))
        sys.exit()
    nulls = []
    for i in range(n):
        rng = random.Random(i)
        if mode0 == 'day': ds = shuffle_time(docs, ('day',), rng)
        elif mode0 == 'daypage': ds = shuffle_time(docs, ('day', 'page'), rng)
        elif mode0 == 'm5': ds = shuffle_time(docs, ('m5',), rng)
        elif mode0 == 'textlen': ds = shuffle_textkey(docs, rng)
        nulls.append(counts(run(ds), unpub))
        if i % 20 == 19: print(f'  {i+1} done', flush=True)
    json.dump({'mode': mode, 'n': n, 'real': real, 'nulls': nulls}, open(HERE / f'c27_{mode}.json', 'w'))
