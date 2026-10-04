import torch, numpy as np, polars as pl, sys
sys.path.insert(0,'../conflicts')
from agents import NAME_RE
from transformers import AutoTokenizer, AutoModelForSequenceClassification
name='j-hartmann/emotion-english-distilroberta-base'
tok=AutoTokenizer.from_pretrained(name); mod=AutoModelForSequenceClassification.from_pretrained(name).to('mps').eval()
txt=[NAME_RE.sub('Sam',s) for s in pl.read_parquet('peer_sents_raw.parquet',columns=['sent'])['sent'].to_list()]
out=np.zeros((len(txt),7),dtype=np.float16)
with torch.no_grad():
    for i in range(0,len(txt),128):
        enc=tok(txt[i:i+128],truncation=True,max_length=96,padding=True,return_tensors='pt').to('mps')
        out[i:i+128]=mod(**enc).logits.softmax(-1).cpu().numpy()
        if i%12800==0: print(i,flush=True)
np.save('emotion.npy',out); print('done')
