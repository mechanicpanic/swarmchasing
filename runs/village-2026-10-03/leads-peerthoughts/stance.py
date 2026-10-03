import numpy as np, polars as pl
from sentence_transformers import SentenceTransformer
from anchors import ANCHORS
m=SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2',device='cpu')
X=np.load('emb.npy').astype(np.float32)
names=list(ANCHORS); S=np.zeros((X.shape[0],len(names)),dtype=np.float32)
for j,k in enumerate(names):
    A=m.encode(ANCHORS[k],normalize_embeddings=True)
    S[:,j]=(X@A.T).max(1)
np.save('stance_scores.npy',S)
P=pl.read_parquet('peer_sents_clustered.parquet')
P=P.with_columns(*[pl.Series('s_'+k,S[:,j]) for j,k in enumerate(names)])
best=S.argmax(1); bs=S.max(1)
P=P.with_columns(pl.Series('stance',[names[i] for i in best]),pl.Series('stance_sim',bs))
P.write_parquet('peer_sents_scored.parquet')
for k in names:
    sub=P.filter(pl.col('stance')==k).sort('stance_sim',descending=True)
    print(f'\n=== {k}  >=0.6:{sub.filter(pl.col("stance_sim")>=0.6).height} >=0.5:{sub.filter(pl.col("stance_sim")>=0.5).height}')
    for band in (0.65,0.55,0.5):
        b=sub.filter((pl.col('stance_sim')>=band)&(pl.col('stance_sim')<band+0.05))
        for r in b.sample(min(3,b.height),seed=0).iter_rows(named=True): print(f'  [{r["stance_sim"]:.2f}] {r["agent"]}: {r["sent"][:170]}')
