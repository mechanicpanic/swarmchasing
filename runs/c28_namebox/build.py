"""C28 (report §13): the name-box test. build.py parses signed lines in wiki_msgs adds into rows.pkl;
ana.py <most|first|self> [strict] computes the borrowed-use share and nulls a-d; repro7.py ports PR #7's test.
OUT (default results/c28/) must exist; WIKI_MSGS overrides the data path."""
"""C28 step 1: signatures on lines each save ADDED, from data/wiki_msgs.parquet (kind=add rows).
Signature regexes copied from PR #7 runs/wiki-june18/signatures_sig.py; line freshness recomputed on our add stream."""
import collections, pickle, re
import polars as pl

D = __import__('os').environ.get('WIKI_MSGS', 'data/wiki_msgs.parquet')
OUT = __import__('os').environ.get('OUT', 'results/c28/')

P_EOL = re.compile(r'(?:^|\s)--\s?([A-Za-z][\w.\-]{1,60}?)[.?!*,;]*\s*(?:\$\(.*|\[M\d+\]|\\n)?\s*$')
P_HDR = re.compile(r'(?:^|\s)--\s([A-Za-z][\w\-]{2,60}):\s')
P_DESC = re.compile(r'(?:^|\s)--\s([A-Za-z][\w]{1,30}\s(?:watcher|helper|team|runner|cohort|scout|agent))[.!]?\s*$', re.I)
P_TILDE = re.compile(r'(?:^|\s)~{1,4}\s?([A-Z][\w\-]{2,60})\s*$')
P_SIGNED = re.compile(r'(?i)\b(?:signed(?:\s+by)?|sig(?:nature)?)\s*[:,]?\s+([A-Za-z][\w\-]{2,60})')
P_DASHU = re.compile(r'[—–]\s?([A-Za-z][\w\-]{2,60})\s*$')
FORMS = [('eol', P_EOL), ('header', P_HDR), ('desc', P_DESC), ('tilde', P_TILDE), ('signed', P_SIGNED), ('emdash', P_DASHU)]
STOP = {'data', 'format', 'header', 'request', 'get', 'url', 'output', 'compressed', 'insecure', 'location', 'silent'}


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def sigs_in(line):
    out = []
    for part in line.split('\\n'):
        for form, p in FORMS:
            for m in p.finditer(part):
                name = m.group(1).rstrip('.-')
                if name.lower() in STOP or len(name) < 3:
                    continue
                out.append((form, name))
    return out


a = (pl.read_parquet(D).filter(pl.col('kind') == 'add').sort(['time', 'seq'])
     .select('id', 'time', 'seq', 'page', 'label', 'ip16', 'rev', 'text'))
revs = collections.OrderedDict()
for r in a.iter_rows(named=True):
    v = revs.setdefault(r['rev'], dict(rev=r['rev'], t=r['time'].timestamp(), time=r['time'].isoformat()[:19],
                                       label=r['label'] or '', page=r['page'], ip16=r['ip16'], lines=[]))
    v['lines'] += [(r['id'], ln) for ln in r['text'].split('\n')]

page_seen = collections.defaultdict(set)
seen = set()
rows = []
for v in revs.values():
    sig_items = []
    for rid, line in v['lines']:
        nl = norm(line)
        if not nl:
            continue
        fresh = 'readd' if nl in page_seen[v['page']] else 'copy' if nl in seen else 'new'
        for form, name in sigs_in(line):
            sig_items.append(dict(form=form, name=name, fresh=fresh, line=line, row_id=rid))
    for _, line in v['lines']:
        nl = norm(line)
        if nl:
            page_seen[v['page']].add(nl); seen.add(nl)
    rows.append(dict(rev_id=v['rev'], t=v['t'], time=v['time'], label=v['label'], page=v['page'], ip16=v['ip16'],
                     sigs=sig_items))
pickle.dump(rows, open(OUT + 'rows.pkl', 'wb'))
c = collections.Counter((s['form'], s['fresh']) for r in rows for s in r['sigs'])
print('revisions with added text', len(rows))
print('sig items by form/freshness', sorted(c.items()))
print('saves with any sig', sum(bool(r['sigs']) for r in rows),
      'saves with a NEW signed line', sum(any(s['fresh'] == 'new' for s in r['sigs']) for r in rows))
