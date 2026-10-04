"""Print matched context (±170 chars) for the first N hits after each event in event_traces.csv (verification aid)."""
import polars as pl, re, sys
from datetime import datetime as D
d = pl.read_csv('event_traces.csv', infer_schema_length=0)
lf = pl.scan_parquet('text_lean.parquet')
want = sys.argv[1:] or None
for r in d.iter_rows(named=True):
    if want and not any(w.lower() in r['event'].lower() for w in want): continue
    h = lf.filter(pl.col('time') >= D.fromisoformat(r['date']), pl.col('text').str.contains(r['regex'])).sort('time').head(4).collect()
    print('##', r['date'], r['event'])
    for x in h.iter_rows(named=True):
        m = re.search(r['regex'], x['text']); s = max(0, m.start() - 170)
        print('  ', str(x['time'])[:16], x['src'], 'human' if x['src'] == 'human_chat' else x['agent'], '|', x['text'][s:m.end() + 170].replace('\n', ' '))
