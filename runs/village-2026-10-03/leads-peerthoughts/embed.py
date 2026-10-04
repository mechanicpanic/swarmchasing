import sys, numpy as np, polars as pl
sys.path.insert(0,'../conflicts')
from agents import NAME_RE
from sentence_transformers import SentenceTransformer
P=pl.read_parquet('peer_sents_raw.parquet',columns=['sent'])
# mask agent names so clusters reflect stance, not identity
txt=[NAME_RE.sub('Agent',s) for s in P['sent'].to_list()]
m=SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2',device='mps')
out=np.lib.format.open_memmap('emb.npy',mode='w+',dtype=np.float16,shape=(len(txt),384))
B=4096
for i in range(0,len(txt),B):
    out[i:i+B]=m.encode(txt[i:i+B],batch_size=128,normalize_embeddings=True,show_progress_bar=False).astype(np.float16)
    print(i,flush=True)
out.flush(); print('done')
