"""Null twin for a PrismQL query on the Village stream, run inline on a subset of rows.
The query only sees rows passing --keep (a Polars SQL WHERE); include every row any leg can match, or the twin lies.
Rows passing --shuffle get their times permuted within --key (fields joined by commas; derived: day, week, month),
--n times; the rest keep their times. Text predicates are evaluated by the engine on the kept rows.
usage: uv run python runs/village_null.py QUERY --keep "kind = 'AGENT_TALK'" --shuffle "agent <> 'GPT-5'" --key day,agent
       [--n 100] [--distinct-last] [--dicts '{"frame": ["hostile", "adversary"]}'] [--data data/village.parquet]"""
import argparse, json, random, statistics, time as _t
import polars as pl
from prismql import PrismQLEngine
from prismql.backends.memory import MemoryBackend

ap = argparse.ArgumentParser()
ap.add_argument('query'); ap.add_argument('--keep', required=True); ap.add_argument('--shuffle', required=True)
ap.add_argument('--key', default='day'); ap.add_argument('--n', type=int, default=100)
ap.add_argument('--data', default='data/village.parquet'); ap.add_argument('--dicts', default='{}')
ap.add_argument('--distinct-last', action='store_true', help='count distinct last events of the groups (query without AGGREGATE)')
a = ap.parse_args()
cols = ['id', 'time', 'kind', 'agent', 'text', 'room', 'of']
df = pl.read_parquet(a.data, columns=cols).sql(f'SELECT * FROM self WHERE {a.keep}')
df = df.with_columns(pl.col('time').dt.strftime('%Y-%m-%dT%H:%M:%S%.6fZ'))
sh = pl.Series(df.sql(f'SELECT ({a.shuffle}) AS s FROM self')['s']).fill_null(False).to_list()
docs = df.to_dicts()
for d in docs:
    d['day'] = d['time'][:10]; d['month'] = d['time'][:7]
    d['week'] = _t.strftime('%G-W%V', _t.strptime(d['day'], '%Y-%m-%d'))
dicts = json.loads(a.dicts)
print(f'rows kept {len(docs)}, shuffled {sum(sh)}', flush=True)

def run(ds):
    ds = sorted(ds, key=lambda d: d['time'])
    eng = PrismQLEngine(search_backend=MemoryBackend(ds, id_field='id'), timestamp_field='time', user_dictionaries=dicts)
    r = eng.execute(a.query)
    if a.distinct_last: return len({g[-1] for g in r})
    return r.to_dict()['value'] if hasattr(r, 'to_dict') else len(r)

t0 = _t.time(); real = run(docs); print(f'real: {real}  ({_t.time()-t0:.1f}s)', flush=True)
keyf = lambda d: tuple(d.get(k) for k in a.key.split(','))
fixed = [d for d, s in zip(docs, sh) if not s]
strata = {}
for d, s in zip(docs, sh):
    if s: strata.setdefault(keyf(d), []).append(d)
nulls = []
for i in range(a.n):
    rng = random.Random(i); out = list(fixed)
    for rows in strata.values():
        times = [d['time'] for d in rows]; rng.shuffle(times)
        out += [{**d, 'time': t} for d, t in zip(rows, times)]
    nulls.append(run(out))
    if i in (9, 49): print(f'  {i+1} done, median so far {statistics.median(nulls)}', flush=True)
nulls.sort(); p95 = nulls[int(0.95 * a.n) - 1]
print(f'null (n={a.n}, times of [{a.shuffle}] shuffled within {a.key}): median {statistics.median(nulls)}  95th {p95}  max {nulls[-1]}')
print(f'share of nulls >= real: {sum(x >= real for x in nulls) / a.n:.3f}')
print('VERDICT:', 'clears 95th' if real > p95 else 'within null')
