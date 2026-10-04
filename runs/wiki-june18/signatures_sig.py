"""Signature vs label analysis for the collusion.wiki export (scratch)."""
import gzip, json, re, collections, pickle
from datetime import datetime

D = '/Users/phosphorus/projects/prismql-data/collusion-wiki/'
OUT = './out/'  # intermediates

revs = [json.loads(l) for l in gzip.open(D + 'revisions.jsonl.gz', 'rt')]
for r in revs:
    r['t'] = datetime.fromisoformat(r['time'].replace('Z', '+00:00')).timestamp()
    r['label'] = r['label'] or ''
revs.sort(key=lambda r: (r['t'], r['page_key'], r['seq']))

# signature patterns, applied per line
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
    for parts in line.split('\\n'):
        for form, p in FORMS:
            for m in p.finditer(parts):
                name = m.group(1).rstrip('.-')
                if name.lower() in STOP or len(name) < 3:
                    continue
                out.append((form, name))
    return out


page_lines = collections.defaultdict(set)   # lines ever present on page
global_first = {}                              # line -> (t, label, page)
rows = []                                      # one per revision
for r in revs:
    body = r['body'].split('\n')
    added_idx = []
    for h in r['hunks']:
        if h['op'] in ('insert', 'replace'):
            added_idx.extend(range(h['b0'], h['b1']))
    added = [body[i] for i in added_idx if i < len(body)]
    pk = r['page_key']
    sig_items = []
    for line in added:
        nl = norm(line)
        if not nl:
            continue
        if nl in page_lines[pk]:
            fresh = 'readd'
        elif nl in global_first:
            fresh = 'copy'
        else:
            fresh = 'new'
        for form, name in sigs_in(line):
            src = global_first.get(nl)
            sig_items.append(dict(form=form, name=name, fresh=fresh, line=line[:300],
                                  src_label=src[1] if src else None, src_page=src[2] if src else None,
                                  src_t=src[0] if src else None))
    for line in body:
        nl = norm(line)
        if nl:
            page_lines[pk].add(nl)
            global_first.setdefault(nl, (r['t'], r['label'], pk))
    rows.append(dict(rev_id=r['rev_id'], t=r['t'], time=r['time'], label=r['label'], page=pk, ip16=r['ip16'],
                     summary=r.get('change_summary'), sigs=sig_items, n_added=len(added)))

pickle.dump(rows, open(OUT + 'rows.pkl', 'wb'))
print('revisions', len(rows))
c = collections.Counter(); cs = collections.Counter()
for row in rows:
    for s in row['sigs']:
        c[(s['form'], s['fresh'])] += 1
    if row['sigs']:
        cs['saves_with_sig'] += 1
    if any(s['fresh'] == 'new' for s in row['sigs']):
        cs['saves_with_new_sig'] += 1
print(sorted(c.items())); print(cs)
