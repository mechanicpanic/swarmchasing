import json, statistics, sys
from pathlib import Path
H = Path(__file__).parent
for mode in sys.argv[1:]:
    p = H / f'c27_{mode}.json'
    if not p.exists(): print(mode, 'missing'); continue
    r = json.load(open(p)); n = r['n']
    print(f'== null {mode} n={n}')
    for v, real in r['real'].items():
        xs = sorted(x[v]['dest_saves'] for x in r['nulls'])
        ge = sum(x >= real['dest_saves'] for x in xs) / n
        p95 = xs[int(0.95 * n) - 1]
        verdict = 'clears 95th' if real['dest_saves'] > p95 else 'within null'
        print(f"  {v:6s} real {real['dest_saves']:4d} (matches {real['matches']:3d}) | null med {statistics.median(xs):6.1f} 95th {p95:4d} max {xs[-1]:4d} | share>=real {ge:.3f} | {verdict}")
