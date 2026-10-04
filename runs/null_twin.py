"""Null twin for a PrismQL query on the wiki stream: shuffle `time` within a key
(default label; probes/deletes keep their times) 200x, re-run the query inline,
report real vs null distribution.  usage: uv run python runs/null_twin.py QUERY [--key ip16] [--shuffle save] [--n 200]
  other streams: --data data/wiki_msgs.parquet --type-field kind --shuffle add --key day  (day = UTC date of `time`)
  text predicates: --dicts '{"confirmed": ["confirmed"]}'"""
import argparse, json, random, statistics, time as _t
from prismql import PrismQLEngine
from prismql.backends.memory import MemoryBackend

ap = argparse.ArgumentParser()
ap.add_argument('query'); ap.add_argument('--key', default='label')
ap.add_argument('--shuffle', default='save', help='event_type whose times get permuted within key')
ap.add_argument('--n', type=int, default=200); ap.add_argument('--data', default='data/collusion_wiki_events.jsonl')
ap.add_argument('--type-field', default='event_type', help='field whose value --shuffle names')
ap.add_argument('--dicts', default='{}', help='JSON object of dictionaries for contains(), as sent to the server')
ap.add_argument('--unit', default='id', help='rows sharing this field move together (rev = whole saves)')
ap.add_argument('--distinct-last', action='store_true', help='count distinct last events of the groups, not matches (query without AGGREGATE)')
a = ap.parse_args()
dicts = json.loads(a.dicts)
if a.data.endswith('.parquet'):
    import polars as pl
    docs = pl.read_parquet(a.data).drop('position', 'emb', strict=False).with_columns(pl.col('time').dt.strftime('%Y-%m-%dT%H:%M:%SZ')).to_dicts()
else:
    docs = [json.loads(l) for l in open(a.data)]
for d in docs:  # derived keys: day, m5 (5-minute stratum); --key may join fields with commas, e.g. day,page
    d['timestamp'] = d['time']; d['day'] = d['time'][:10]; d['m5'] = d['time'][:15] + str(int(d['time'][15]) // 5 * 5)
keyf = lambda d: tuple(d.get(k) for k in a.key.split(','))

def run(ds):
    ds = sorted(ds, key=lambda d: d['time'])
    eng = PrismQLEngine(search_backend=MemoryBackend(ds, id_field='id'), timestamp_field='time', user_dictionaries=dicts)
    r = eng.execute(a.query)
    if a.distinct_last: return len({g[-1] for g in r})
    return r.to_dict()['value'] if hasattr(r, 'to_dict') else len(r)

t0=_t.time(); real = run(docs); print(f'real: {real}  ({_t.time()-t0:.1f}s)', flush=True)
by_key = {}
for d in docs:
    if d[a.type_field] == a.shuffle: by_key.setdefault(keyf(d), {}).setdefault(d[a.unit], []).append(d)
nulls = []
for i in range(a.n):
    rng = random.Random(i); sh = []
    for k, units in by_key.items():
        rows = list(units.values()); times = [u[0]['time'] for u in rows]; rng.shuffle(times)
        sh += [{**d, 'time': t, 'timestamp': t} for u, t in zip(rows, times) for d in u]
    nulls.append(run([d for d in docs if d[a.type_field] != a.shuffle] + sh))
    if i in (9, 49): print(f'  {i+1} done, median so far {statistics.median(nulls)}', flush=True)
nulls.sort()
print(f'null (n={a.n}, {a.shuffle} times of whole {a.unit} units shuffled within {a.key}): median {statistics.median(nulls)}  95th {nulls[int(0.95*a.n)-1]}  max {nulls[-1]}')
print('VERDICT:', 'clears 95th' if real > nulls[int(0.95*a.n)-1] else 'within null')
