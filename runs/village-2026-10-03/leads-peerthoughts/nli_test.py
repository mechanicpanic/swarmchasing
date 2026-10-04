import time, torch, polars as pl
from transformers import AutoTokenizer, AutoModelForSequenceClassification
for name in ['cross-encoder/nli-deberta-v3-xsmall','j-hartmann/emotion-english-distilroberta-base']:
    tok=AutoTokenizer.from_pretrained(name); mod=AutoModelForSequenceClassification.from_pretrained(name).to('mps').eval()
    print(name, mod.config.id2label)
    P=pl.read_parquet('peer_sents_raw.parquet',columns=['sent']).sample(1024,seed=3)['sent'].to_list()
    t=time.time()
    with torch.no_grad():
        for i in range(0,1024,128):
            b=P[i:i+128]
            if 'nli' in name: enc=tok(b,['The writer expresses a personal opinion or feeling about another agent.']*len(b),truncation=True,max_length=96,padding=True,return_tensors='pt').to('mps')
            else: enc=tok(b,truncation=True,max_length=96,padding=True,return_tensors='pt').to('mps')
            o=mod(**enc).logits.softmax(-1).cpu()
    print('per s', 1024/(time.time()-t))
