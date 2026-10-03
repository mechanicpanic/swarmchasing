import numpy as np, polars as pl
from sentence_transformers import SentenceTransformer
from anchors import ANCHORS, NEUTRAL
m=SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2',device='cpu')
X=np.load('emb.npy').astype(np.float32)
N=(X@m.encode(NEUTRAL,normalize_embeddings=True).T).max(1)
S=np.load('stance_scores.npy'); names=list(ANCHORS)
D=S-N[:,None]
np.save('stance_margin.npy',D)
P=pl.read_parquet('peer_sents_raw.parquet',columns=['agent','sent'])
best=D.argmax(1); bm=D.max(1)
P=P.with_columns(pl.Series('stance',[names[i] for i in best]),pl.Series('margin',bm),pl.Series('ssim',S.max(1)),pl.Series('nsim',N))
P=P.filter(pl.col('sent').str.split(' ').list.len()>=6)
for k in names:
    sub=P.filter(pl.col('stance')==k)
    print(f'\n=== {k} m>.15:{sub.filter(pl.col("margin")>.15).height} m>.1:{sub.filter(pl.col("margin")>.1).height} m>.05:{sub.filter(pl.col("margin")>.05).height}')
    for lo,hi in ((.15,1),(.1,.15),(.05,.1)):
        b=sub.filter((pl.col('margin')>=lo)&(pl.col('margin')<hi))
        for r in b.sample(min(3,b.height),seed=0).iter_rows(named=True): print(f'  [{r["margin"]:.2f}] {r["agent"]}: {r["sent"][:160]}')
