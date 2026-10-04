import numpy as np, polars as pl
KEYS=['admire','worry','distrust','annoyed','mindread','rival','grateful','protect','amused','defer','critic','selfcomp']
def load():
    A=np.load('nli_pool.npy').astype(np.float32)
    pool=pl.read_parquet('pool.parquet',columns=['rid'])
    done=[k for j,k in enumerate(KEYS) if A[:,j].max()>0]
    N=pool.with_columns(*[pl.Series('n_'+k,A[:,KEYS.index(k)]) for k in done])
    P=pl.read_parquet('peer_sents_all_scores.parquet').join(N,on='rid',how='inner')
    return P.with_columns((pl.col('e_anger')+pl.col('e_disgust')).alias('neg')), done
