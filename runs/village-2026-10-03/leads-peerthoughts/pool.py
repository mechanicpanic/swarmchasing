import numpy as np, polars as pl
from sklearn.cluster import KMeans
from anchors import ANCHORS
E=np.load('emotion.npy').astype(np.float32); labs=['anger','disgust','fear','joy','neutral','sadness','surprise']
D=np.load('stance_margin.npy'); names=list(ANCHORS)
P=pl.read_parquet('peer_sents_raw.parquet').with_row_index('rid')
P=P.with_columns(*[pl.Series('e_'+l,E[:,i]) for i,l in enumerate(labs)],
                 pl.Series('anchor',[names[i] for i in D.argmax(1)]),pl.Series('anchor_margin',D.max(1)))
P=P.with_columns((1-pl.col('e_neutral')).alias('affect'), pl.col('sent').str.split(' ').list.len().alias('nw'))
print(P.select((pl.col('affect')>0.5).sum().alias('a5'),(pl.col('affect')>0.7).sum().alias('a7'),(pl.col('anchor_margin')>0.1).sum().alias('m1')))
pool=P.filter((pl.col('nw')>=6)&((pl.col('affect')>0.6)|(pl.col('anchor_margin')>0.12)))
print('pool',pool.height)
X=np.load('emb.npy',mmap_mode='r')[pool['rid'].to_numpy()].astype(np.float32)
K=40; km=KMeans(K,random_state=0,n_init=4).fit(X)
pool=pool.with_columns(pl.Series('pcluster',km.labels_))
P.write_parquet('peer_sents_all_scores.parquet'); pool.write_parquet('pool.parquet')
with open('pool_samples.txt','w') as f:
  for c in range(K):
    s=pool.filter(pl.col('pcluster')==c)
    em=s.select([pl.col('e_'+l).mean().round(2) for l in labs]).row(0)
    f.write(f'\n=== P{c} n={s.height} emo={dict(zip(labs,em))} top_anchor={s["anchor"].mode().to_list()[:1]}\n')
    for r in s.sample(min(12,s.height),seed=c).iter_rows(named=True): f.write(f'  - {r["agent"]}: {r["sent"][:180]}\n')
