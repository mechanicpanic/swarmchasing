import numpy as np, polars as pl, sys
from sklearn.cluster import MiniBatchKMeans
X=np.load('emb.npy').astype(np.float32)
K=int(sys.argv[1]) if len(sys.argv)>1 else 80
km=MiniBatchKMeans(n_clusters=K,random_state=0,batch_size=8192,n_init=3).fit(X)
lab=km.labels_
d=(X*km.cluster_centers_[lab]).sum(1)/np.linalg.norm(km.cluster_centers_[lab],axis=1)
np.save('centers.npy',km.cluster_centers_)
P=pl.read_parquet('peer_sents_raw.parquet').with_columns(pl.Series('cluster',lab),pl.Series('centrality',d))
P.write_parquet('peer_sents_clustered.parquet')
with open('cluster_samples.txt','w') as f:
    for c in range(K):
        sub=P.filter(pl.col('cluster')==c)
        f.write(f'\n=== C{c} n={sub.height}\n')
        top=sub.sort('centrality',descending=True).head(4)
        rnd=sub.sample(min(8,sub.height),seed=c)
        for s in pl.concat([top,rnd])['sent']: f.write('  - '+s[:200].replace('\n',' ')+'\n')
print('ok')
