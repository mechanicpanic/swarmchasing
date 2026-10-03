import torch, numpy as np, polars as pl, sys
sys.path.insert(0,'../conflicts')
from agents import NAME_RE
from transformers import AutoTokenizer, AutoModelForSequenceClassification
H={'admire':"The writer praises or admires Sam's work.",
   'worry':"The writer is worried about Sam or feels sorry for Sam.",
   'distrust':"The writer doubts that what Sam said is true.",
   'annoyed':"The writer is annoyed or frustrated with Sam.",
   'mindread':"The writer speculates about what Sam is thinking, feeling or experiencing.",
   'rival':"The writer is competing with Sam.",
   'grateful':"The writer is grateful to Sam.",
   'protect':"The writer wants to defend or protect Sam.",
   'amused':"The writer finds Sam funny or charming.",
   'defer':"The writer defers to Sam's judgment.",
   'critic':"The writer thinks Sam made a mistake.",
   'selfcomp':"The writer compares themself to Sam."}
name='cross-encoder/nli-deberta-v3-xsmall'
tok=AutoTokenizer.from_pretrained(name); mod=AutoModelForSequenceClassification.from_pretrained(name).to('mps').eval()
pool=pl.read_parquet('pool.parquet',columns=['rid','sent'])
# mask: subject names -> Sam (all agents named); self-name stays masked too (rare)
txt=[NAME_RE.sub('Sam',s) for s in pool['sent'].to_list()]
out=np.zeros((len(txt),len(H)),dtype=np.float16)
with torch.no_grad():
  for j,(k,h) in enumerate(H.items()):
    for i in range(0,len(txt),256):
        b=txt[i:i+256]
        enc=tok(b,[h]*len(b),truncation=True,max_length=112,padding=True,return_tensors='pt').to('mps')
        p=mod(**enc).logits.softmax(-1).cpu().numpy()
        out[i:i+256,j]=p[:,1]
    print(k,flush=True); np.save('nli_pool.npy',out)
pool.select('rid').with_columns(*[pl.Series('n_'+k,out[:,j]) for j,k in enumerate(H)]).write_parquet('nli_pool.parquet')
print('done')
