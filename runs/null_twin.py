"""Null twin for a PrismQL query on the wiki stream: shuffle `time` within a key
(default label; probes/deletes keep their times) 200x, re-run the query inline,
report real vs null distribution.  usage: uv run python runs/null_twin.py QUERY [--key ip16] [--shuffle save] [--n 200]
  other streams: --data data/wiki_msgs.parquet --type-field kind --shuffle add --key day  (day = UTC date of `time`)"""
import argparse, json, random, statistics, time as _t
from prismql import PrismQLEngine
from prismql.backends.memory import MemoryBackend

ap = argparse.ArgumentParser()
ap.add_argument('query'); ap.add_argument('--key', default='label')
ap.add_argument('--shuffle', default='save', help='event_type whose times get permuted within key')
ap.add_argument('--n', type=int, default=200); ap.add_argument('--data', default='data/collusion_wiki_events.jsonl')
ap.add_argument('--type-field', default='event_type', help='field whose value --shuffle names')
a = ap.parse_args()
if a.data.endswith('.parquet'):
    import polars as pl
    docs = pl.read_parquet(a.data).drop('position', 'emb', strict=False).with_columns(pl.col('time').dt.strftime('%Y-%m-%dT%H:%M:%SZ')).to_dicts()
else:
    docs = [json.loads(l) for l in open(a.data)]
for d in docs: d['timestamp'] = d['time']; d['day'] = d['time'][:10]

def run(ds):
    ds = sorted(ds, key=lambda d: d['time'])
    eng = PrismQLEngine(search_backend=MemoryBackend(ds, id_field='id'), timestamp_field='time')
    r = eng.execute(a.query)
    return r.to_dict()['value'] if hasattr(r, 'to_dict') else len(r)

t0=_t.time(); real = run(docs); print(f'real: {real}  ({_t.time()-t0:.1f}s)', flush=True)
by_key = {}
for d in docs:
    if d[a.type_field] == a.shuffle: by_key.setdefault(d.get(a.key), []).append(d)
nulls = []
for i in range(a.n):
    rng = random.Random(i); sh = []
    for k, grp in by_key.items():
        times = [d['time'] for d in grp]; rng.shuffle(times)
        sh += [{**d, 'time': t, 'timestamp': t} for d, t in zip(grp, times)]
    nulls.append(run([d for d in docs if d[a.type_field] != a.shuffle] + sh))
    if i in (9, 49): print(f'  {i+1} done, median so far {statistics.median(nulls)}', flush=True)
nulls.sort()
print(f'null (n={a.n}, {a.shuffle} times shuffled within {a.key}): median {statistics.median(nulls)}  95th {nulls[int(0.95*a.n)-1]}  max {nulls[-1]}')
print('VERDICT:', 'clears 95th' if real > nulls[int(0.95*a.n)-1] else 'within null')
