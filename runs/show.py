"""Pretty-print hydrated groups from a prismql-server response on stdin, with a text snippet around the first dictionary hit."""
import json, sys, re, tomllib
cfg = tomllib.load(open('prismql.toml','rb'))
terms = cfg['corpora']['revisions']['dictionaries']
r = json.load(sys.stdin)
slots = sys.argv[1:]  # optional: dictionary name per leg, e.g. moderation backup
if 'error' in r: print('ERROR', r['error']); sys.exit()
for g in r.get('results', []):
    print('— группа —')
    for i, e in enumerate(g['events']):
        t = (e.get('text') or '').replace('\n', ' ')
        hit = None
        order = ([slots[i]] if i < len(slots) else []) + [d for d in terms if i >= len(slots) or d != slots[i]]
        for d in order:
            ws = terms[d]
            for w in ws:
                m = re.search(re.escape(w), t, re.I)
                if m: hit = (d, m); break
            if hit: break
        s = t[max(0, hit[1].start()-70):hit[1].end()+70] if hit else t[:140]
        lab = e.get('label') or '-'; fam = e.get('page_family') or '-'
        print(f"  {e['time']}  {lab:26s} {e['ip16']:8s} {fam:22s} [{hit[0] if hit else '?'}] …{s}…")
print('групп в ответе:', len(r.get('results', [])), '| truncated:', r.get('truncated'))
