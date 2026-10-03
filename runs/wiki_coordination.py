"""Coordination traces in the collusion.wiki export (DseWiki incident). Identity = label, often one-off, so:
 (1) handles addressed inside messages (known labels mentioned in text written under another label),
 (2) signatures '-- Name' in revision bodies vs the revision's label,
 (3) broadcast: distinct messages replicated across many pages,
 (4) hub pages: pages written by the most distinct labels."""
import gzip, json, re, ast, collections, polars as pl
D = 'data/collusion_wiki/'
labels = [json.loads(l) for l in gzip.open(D + 'labels.jsonl.gz', 'rt')]
lab = {x['label'] for x in labels if x.get('label') and len(x['label']) >= 6 and not x['label'].isalpha() or (x.get('label') and len(x['label']) >= 9)}
recs = [json.loads(l) for l in gzip.open(D + 'records.jsonl.gz', 'rt')]
rv = pl.read_ndjson('data/collusion_wiki_revisions.jsonl')
print(f"records {len(recs)}, revisions {rv.height}, labels {len(labels)} (candidate handles ≥6 chars w/ digits or ≥9 chars: {len(lab)})")
# (1) addressed handles in messages: 'X ping', '@X', 'X:' at start, 'to X', or just X anywhere
pat = re.compile(r'\b(' + '|'.join(re.escape(x) for x in sorted(lab, key=len, reverse=True)) + r')\b')
addr = collections.Counter(); ping = collections.Counter()
for r in recs:
    t = r['text'] or ''
    for m in set(pat.findall(t)): addr[m] += 1
    for m in re.findall(r'\b(\w{5,40})\s+ping\b|@(\w{5,40})', t):
        ping[m[0] or m[1]] += 1
print("\n(1) handles most often named inside messages:", addr.most_common(12))
print("    explicit 'X ping' / '@X':", ping.most_common(10))
# (2) signatures
sig = rv.select('label', 'time', pl.col('text').str.extract_all(r'--\s*\[?\[?([A-Z][A-Za-z0-9]{3,40})').alias('s')).explode('s').drop_nulls('s')
s = sig.group_by('s').agg(pl.len().alias('signed_revisions'), pl.col('label').n_unique().alias('distinct_labels_posting_it'),
                           (pl.col('label') != pl.col('s')).mean().round(2).alias('share_not_own_label')).sort('signed_revisions', descending=True)
print("\n(2) signatures '-- Name' in bodies (a signature carried by many labels = quoted/copied, or one author behind many labels):"); print(s.head(10))
# (3) broadcast
b = sorted(recs, key=lambda r: -len(r['origins'] if isinstance(r['origins'], list) else ast.literal_eval(r['origins'])))
print("\n(3) most replicated messages:")
for r in b[:6]:
    o = r['origins'] if isinstance(r['origins'], list) else ast.literal_eval(r['origins'])
    pages = {x['title'] for x in o}; dates = sorted(x.get('source_date_literal','') for x in o)
    print(f"  {len(o):4d} origins on {len(pages):3d} pages, {dates[0][:16]} → {dates[-1][:16]}: {r['text'][:150]!r}")
# (4) hub pages
h = rv.group_by('page', 'page_family').agg(pl.col('label').n_unique().alias('labels'), pl.len().alias('revisions'), pl.col('time').min().alias('first'), pl.col('time').max().alias('last')).sort('labels', descending=True)
print("\n(4) pages written by the most distinct labels:"); print(h.head(8))
