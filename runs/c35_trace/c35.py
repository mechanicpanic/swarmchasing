"""C35: the name box traced row by row. For every signed save whose label is not one of its signatures (C28's
mismatches; also C28's strict borrowed subset), trace (a) the label's previous save anywhere and (b) the signer's own
name as a label (previous / next save under it, and whether another signer wears it within +-10 min).
Signatures: C28 build.py rows.pkl (PR #7 parse, new signed lines only; run build.py first with OUT=$OUT/), or with
--sigcol the `signature` column of wiki_msgs. Save stream: every revision with a label (revisions export), minus
[Admin*], the 17 'earlier_revisions_not_published', revs carrying the Loop broadcast and redirect bodies.
Nulls: labels permuted among saves within (day, page) and within the hour; every trace recomputed.
usage: REPO=. OUT=results/c35/ python runs/c35_trace/c35.py [--nohub] [--noexcl] [--sigcol] [--nrep 300] [--dump]"""
import bisect, collections, gzip, json, os, pickle, random, re, statistics, sys
from datetime import datetime
from functools import lru_cache

import polars as pl

REPO, OUT = os.environ.get('REPO', '.'), os.environ.get('OUT', 'results/c35/')
HUB, BROADCAST, W = 'dse~WillkommenImWiki', '146d7f0c0cfc7856', 600
REDIR = re.compile(r'(?i)^\s*#(redirect|weiterleitung)')
ARGS = sys.argv[1:]
NREP = int(ARGS[ARGS.index('--nrep') + 1]) if '--nrep' in ARGS else 300


def load():
    revs = [json.loads(x) for x in gzip.open(f'{REPO}/data/collusion_wiki/revisions.jsonl.gz', 'rt')]
    wm = pl.read_parquet(f'{REPO}/data/wiki_msgs.parquet', columns=['rev', 'time', 'seq', 'kind', 'text', 'text_key', 'signature'])
    bc = set(wm.filter(pl.col('text_key') == BROADCAST)['rev'])
    S = []
    for r in revs:
        L = r.get('label') or ''
        if not L or L.startswith('[Admin'):
            continue
        if '--noexcl' not in ARGS and (r.get('diff_base_reason') == 'earlier_revisions_not_published'
                                       or r['rev_id'] in bc or REDIR.match(r.get('body') or '')):
            continue
        if '--nohub' in ARGS and r['page_key'] == HUB:
            continue
        t = datetime.fromisoformat(r['time'].replace('Z', '+00:00')).timestamp()
        S.append(dict(rev=r['rev_id'], t=t, label=L, page=r['page_key'], names=[], line=''))
    S.sort(key=lambda s: s['t'])  # stable: export order breaks ties
    by_rev = {s['rev']: s for s in S}
    if '--sigcol' in ARGS:  # wiki_msgs.signature: last "-- Name" line of each added hunk, any add_type
        for rev, sig, text in (wm.filter((pl.col('kind') == 'add') & pl.col('signature').is_not_null()).sort('time', 'seq')
                               .select('rev', 'signature', 'text').iter_rows()):
            if rev in by_rev and sig not in by_rev[rev]['names']:
                by_rev[rev]['names'].append(sig); by_rev[rev]['line'] = [ln for ln in text.splitlines() if sig in ln][-1]
    else:  # C28/PR #7: names on NEW signed lines; signer = last one
        for r in pickle.load(open(OUT + 'rows.pkl', 'rb')):
            new = [x for x in r['sigs'] if x['fresh'] == 'new']
            if new and r['rev_id'] in by_rev:
                s = by_rev[r['rev_id']]
                s['names'] = list(dict.fromkeys(x['name'] for x in new))
                s['signer'] = new[-1]['name']; s['line'] = new[-1]['line']
    seen = set()
    for i, s in enumerate(S):
        s.setdefault('signer', s['names'][-1] if s['names'] else None)
        k = re.sub(r'[^A-Za-z0-9]', '', s['line'])
        s['resave'] = bool(s['names']) and k in seen
        if s['names']:
            seen.add(k)
        s['i'], s['day'], s['hour'] = i, int(s['t'] // 86400), int(s['t'] // 3600)
    return S


@lru_cache(maxsize=None)
def near(a, b):  # C28/PR #7 near-variant: case, edit distance <=3, or containment (>=5 chars)
    a2, b2 = a.lower(), b.lower()
    if a2 == b2 or (min(len(a2), len(b2)) >= 5 and (a2 in b2 or b2 in a2)):
        return True
    if abs(len(a2) - len(b2)) > 3:
        return False
    prev = list(range(len(b2) + 1))
    for i, ca in enumerate(a2, 1):
        cur = [i]
        for j, cb in enumerate(b2, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] <= 3


def trace(S, labels):
    """labels[i] = label of save i. Returns per-mismatch trace dicts (all mismatches; 'strict' flag)."""
    pos = collections.defaultdict(list)
    for i, L in enumerate(labels):
        pos[L].append(i)
    cnt = collections.defaultdict(collections.Counter); first = {}
    for i, s in enumerate(S):
        for nm in s['names']:
            cnt[labels[i]][nm] += 1; first.setdefault((labels[i], nm), i)
    owner = {L: max(c, key=lambda k: (c[k], -first[(L, k)])) for L, c in cnt.items()}
    spos = collections.defaultdict(list)  # saves signed by each name (labels play no part)
    for i, s in enumerate(S):
        for nm in s['names']:
            spos[nm].append(i)
    out = []
    for i, s in enumerate(S):
        L, names = labels[i], s['names']
        if not names or L in names:
            continue
        o, sg, t = owner[L], s['signer'], s['t']
        strict = not s['resave'] and not any(nm == o or near(nm, o) or near(nm, L) for nm in names)
        tr = dict(i=i, L=L, S=sg, owner=o, strict=strict)
        p = pos[L]; k = bisect.bisect_left(p, i)
        if k == 0:
            tr['a'] = 'first'
        else:
            j = S[p[k - 1]]
            tr['a_lag'] = t - j['t']; tr['a_same'] = j['page'] == s['page']; tr['a_j'] = j['i']
            tr['a'] = ('self' if sg in j['names'] else 'owner' if o in j['names'] else 'other' if j['names'] else 'unsigned')
        q = pos.get(sg, [])
        k = bisect.bisect_left(q, i)
        tr['b_ever'] = bool(q)
        for side, idx in (('prev', q[k - 1] if k > 0 else None), ('next', q[k] if k < len(q) else None)):
            if idx is not None:
                m = S[idx]
                tr[f'b_{side}_lag'] = abs(t - m['t']); tr[f'b_{side}_same'] = m['page'] == s['page']
                tr[f'b_{side}'] = 'own' if sg in m['names'] else 'other' if m['names'] else 'unsigned'
                tr[f'b_{side}_j'] = idx
        # chain: the signer's own name worn as a label by ANOTHER signer within +-W; swap: that wearer signs L or owner(L)
        lo = bisect.bisect_left([S[x]['t'] for x in q], t - W) if q else 0
        chain = swap = False
        for x in q[lo:]:
            m = S[x]
            if m['t'] > t + W:
                break
            if x != i and m['names'] and sg not in m['names']:
                chain = True
                swap = swap or L in m['names'] or o in m['names']
        tr['chain'], tr['swap'] = chain, swap
        # sticky: the signer's adjacent signed saves (before / after, any page) carry the same label
        q2 = spos[sg]; k2 = bisect.bisect_left(q2, i)
        tr['stick_prev'] = k2 > 0 and labels[q2[k2 - 1]] == L and t - S[q2[k2 - 1]]['t'] <= W
        tr['stick_next'] = k2 + 1 < len(q2) and labels[q2[k2 + 1]] == L and S[q2[k2 + 1]]['t'] - t <= W
        out.append(tr)
    return out


def stats(trs):
    n = len(trs) or 1
    has = [x for x in trs if x['a'] != 'first']
    lags = [x['a_lag'] for x in has]
    st = dict(n=len(trs), first=sum(x['a'] == 'first' for x in trs) / n,
              a_lag_med=statistics.median(lags) if lags else float('nan'),
              a_le60=sum(v <= 60 for v in lags) / n, a_le600=sum(v <= W for v in lags) / n,
              a_le3600=sum(v <= 3600 for v in lags) / n,
              a_same=sum(x['a_same'] for x in has) / (len(has) or 1),
              a_same_le600=sum(x['a_same'] and x['a_lag'] <= W for x in has) / n)
    for c in ('self', 'owner', 'other', 'unsigned'):
        st['a_' + c] = sum(x['a'] == c for x in trs) / n
        st['a_' + c + '_le600'] = sum(x['a'] == c and x['a_lag'] <= W for x in has) / n
    st['b_ever'] = sum(x['b_ever'] for x in trs) / n
    for side in ('prev', 'next'):
        st[f'b_{side}_le600'] = sum(x.get(f'b_{side}_lag', 1e18) <= W for x in trs) / n
        st[f'b_{side}_other_le600'] = sum(x.get(f'b_{side}_lag', 1e18) <= W and x.get(f'b_{side}') == 'other' for x in trs) / n
    st['chain'] = sum(x['chain'] for x in trs) / n
    st['swap'] = sum(x['swap'] for x in trs) / n
    st['stick_prev'] = sum(x['stick_prev'] for x in trs) / n
    st['stick_next'] = sum(x['stick_next'] for x in trs) / n
    return st


def permute(S, key, rng, only=None):
    """Shuffle labels within blocks of key(save); with `only`, among those save indices alone."""
    blocks = collections.defaultdict(list)
    for i, s in enumerate(S):
        if only is None or i in only:
            blocks[key(s)].append(i)
    labels = [s['label'] for s in S]
    for idx in blocks.values():
        if len(idx) > 1:
            v = [labels[i] for i in idx]; rng.shuffle(v)
            for i, L in zip(idx, v):
                labels[i] = L
    return labels


def main():
    S = load()
    real_labels = [s['label'] for s in S]
    real = trace(S, real_labels)
    MIS, STR = {x['i'] for x in real}, {x['i'] for x in real if x['strict']}
    # all/strict: the mismatch set as recomputed in each shuffle (the brief's null; its population shifts);
    # @real: only the saves that are mismatches (strict) in the real data, still mismatched after the shuffle
    scopes = {'all': lambda tr: tr, 'strict': lambda tr: [x for x in tr if x['strict']],
              'all@real': lambda tr: [x for x in tr if x['i'] in MIS], 'strict@real': lambda tr: [x for x in tr if x['i'] in STR]}
    print(f'saves {len(S)}; signed {sum(bool(s["names"]) for s in S)}; mismatches {len(real)}; '
          f'strict {sum(x["strict"] for x in real)}; args {ARGS}')
    pickle.dump(dict(S=S, real=real), open(OUT + 'c35_real' + '_'.join(a.strip('-') for a in ARGS if a != '--dump') + '.pkl', 'wb'))
    lags = sorted(x['a_lag'] for x in real if 'a_lag' in x)
    if lags:
        print('a-lag quantiles (s) 10/25/50/75/90:', [round(lags[int(q * (len(lags) - 1))]) for q in (.1, .25, .5, .75, .9)])
    if '--nrep' in ARGS and NREP == 0:
        for sc, f in scopes.items():
            print(sc, {k: round(v, 3) for k, v in stats(f(real)).items()})
        return
    dp, hr = (lambda s: (s['day'], s['page'])), (lambda s: s['hour'])
    nulls = {'day,page': (dp, None), 'hour': (hr, None), 'day,page|mismatches only': (dp, MIS),
             'hour|mismatches only': (hr, MIS), 'day|mismatches only': ((lambda s: s['day']), MIS)}
    for nn, (key, only) in nulls.items():
        rng = random.Random(35)
        sims = [trace(S, permute(S, key, rng, only)) for _ in range(NREP)]
        for sc, f in scopes.items():
            rs = stats(f(real)); ns = [stats(f(x)) for x in sims]
            print(f'\n== null {nn}, scope {sc}, n={NREP}')
            for k, v in rs.items():
                vs = sorted(x[k] for x in ns if x[k] == x[k])
                if not vs:
                    continue
                ge = sum(x >= v for x in vs) / len(vs); le = sum(x <= v for x in vs) / len(vs)
                print(f'  {k:22s} real {v:10.3f} | null median {statistics.median(vs):10.3f} '
                      f'[{vs[int(.025 * len(vs))]:.3f}, {vs[int(.975 * len(vs)) - 1]:.3f}]  p>= {ge:.3f} p<= {le:.3f}')


if __name__ == '__main__':
    main()
