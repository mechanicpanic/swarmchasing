import numpy as np, polars as pl
D = pl.read_parquet(__import__("os").environ.get("WIKI_MSGS", "data/wiki_msgs.parquet"))
S = pl.read_parquet('c29_authored.parquet')
R = pl.read_csv('c29_signatures.csv')
targets = set(R['sig'])
sigs = set(S['sig'])
lab2sig = S.group_by('label').agg(pl.col('sig').unique()).to_dict(as_series=False)
lab2sig = dict(zip(lab2sig['label'], map(set, lab2sig['sig'])))
revs = D.unique('rev').select('rev', 'label', 'time').sort('time')
lt = revs.group_by('label').agg(pl.col('time')).to_dict(as_series=False)
lt = {l: np.array(t, dtype='datetime64[us]') for l, t in zip(lt['label'], lt['time'])}
def kind(sig, lab):
    if lab == sig: return 'own'
    if lab in sigs or (lab2sig.get(lab, set()) - {sig}): return 'borrowed'
    if lab2sig.get(lab, set()) <= {sig}:
        return 'throwaway'
    return 'generic'
S = S.with_columns(pl.struct('sig', 'label').map_elements(lambda r: kind(r['sig'], r['label']), return_dtype=pl.String).alias('lk'))
# borrowed label used by some other save in the 10 min before
def recent(r):
    t = np.datetime64(r['time'].replace(tzinfo=None), 'us'); ts = lt.get(r['label'], np.array([], 'datetime64[us]'))
    return bool(((ts < t) & (ts >= t - np.timedelta64(600, 's'))).any())
def ever_before(r):
    t = np.datetime64(r['time'].replace(tzinfo=None), 'us'); ts = lt.get(r['label'], np.array([], 'datetime64[us]'))
    return bool((ts < t).any())
S = S.with_columns(pl.struct('time', 'label').map_elements(recent, return_dtype=pl.Boolean).alias('used_10m_before'),
                   pl.struct('time', 'label').map_elements(ever_before, return_dtype=pl.Boolean).alias('used_before'))
T = S.filter(pl.col('sig').is_in(targets))
print('49 sigs, label kinds over their authored saves:'); print(T['lk'].value_counts().sort('count', descending=True))
mm = T.filter(pl.col('lk') != 'own'); print('mismatched saves', mm.height, mm['lk'].value_counts(normalize=True))
print('all signers, mismatched:'); A = S.filter(pl.col('lk') != 'own'); print(A.height, A['lk'].value_counts(normalize=True))
b = T.filter(pl.col('lk') == 'borrowed')
print('borrowed saves among 49:', b.height, 'label used by another save in prior 10 min:', b['used_10m_before'].mean(), 'ever before:', b['used_before'].mean())
per = T.group_by('sig').agg(pl.len().alias('n'), *[(pl.col('lk') == k).sum().alias(k) for k in ['own', 'throwaway', 'borrowed', 'generic']])
per.write_csv('c29_labelkinds.csv')
pl.Config.set_tbl_rows(60); print(per.sort('n', descending=True))
T.write_parquet('c29_authored_targets.parquet')
