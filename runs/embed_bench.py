"""Pick an embedder on our own data: 20k-row sample of the Village stream (12k THOUGHT, 6k AGENT_TALK, 2k other),
six probe questions, top-5 per model, encode speed on MPS. Output: results/embed_bench.txt"""
import time, sys, numpy as np, polars as pl, torch
from sentence_transformers import SentenceTransformer
df = pl.read_parquet('data/village_events.parquet', columns=['kind','agent','text','created_at']).filter(pl.col('text').is_not_null() & (pl.col('text').str.len_chars() > 20))
S = pl.concat([df.filter(pl.col('kind')=='THOUGHT').sample(12000, seed=1), df.filter(pl.col('kind')=='AGENT_TALK').sample(6000, seed=1),
               df.filter(~pl.col('kind').is_in(['THOUGHT','AGENT_TALK'])).sample(2000, seed=1)])
docs = S['text'].to_list()
Q = ["We are being watched, tested or evaluated by the researchers who run this experiment.",
     "I am blocked and should ask a human to help me.",
     "I am giving up on this task; it is not working and I will stop trying.",
     "I claimed more progress than I actually made; my earlier report was wrong.",
     "I want to contact people outside the village by email or social media.",
     "Another agent's claim looks false and I do not trust it."]
# (name, query prefix, doc prefix, extra kwargs, prompt_name for queries)
M = [("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "", "", {}, None),
     ("BAAI/bge-small-en-v1.5", "Represent this sentence for searching relevant passages: ", "", {}, None),
     ("BAAI/bge-base-en-v1.5", "Represent this sentence for searching relevant passages: ", "", {}, None),
     ("nomic-ai/nomic-embed-text-v1.5", "search_query: ", "search_document: ", {"trust_remote_code": True}, None),
     ("google/embeddinggemma-300m", "task: search result | query: ", "title: none | text: ", {}, None),
     ("Qwen/Qwen3-Embedding-0.6B", "", "", {}, "query"),
     ("ibm-granite/granite-embedding-english-r2", "", "", {}, None),
     ("ibm-granite/granite-embedding-small-english-r2", "", "", {}, None),
     ("Snowflake/snowflake-arctic-embed-l-v2.0", "", "", {}, "query")]
only = sys.argv[1:] 
out = open('results/embed_bench.txt', 'a')
def say(*a):
    print(*a); print(*a, file=out); out.flush()
for name, qp, dp, kw, pn in M:
    if only and not any(o in name for o in only): continue
    try:
        m = SentenceTransformer(name, device='mps', **kw)
    except Exception as e:
        say(f"\n##### {name}: LOAD FAILED {type(e).__name__}: {str(e)[:200]}"); continue
    m.max_seq_length = min(512, m.max_seq_length or 512) if 'MiniLM' not in name else 128
    t0 = time.time(); D = m.encode([dp + d for d in docs], batch_size=64, normalize_embeddings=True, convert_to_numpy=True); dt = time.time() - t0
    qs = m.encode(Q, prompt_name=pn, normalize_embeddings=True) if pn else m.encode([qp + q for q in Q], normalize_embeddings=True)
    say(f"\n##### {name}  dim={D.shape[1]} max_seq={m.max_seq_length}  encode {len(docs)} docs in {dt:.0f}s = {len(docs)/dt:.0f}/s  -> full 570k stream ≈ {569540/(len(docs)/dt)/60:.0f} min")
    for q, qv in zip(Q, qs):
        sc = D @ qv; top = np.argsort(-sc)[:5]
        say(f"  Q: {q}")
        for i in top:
            r = S.row(int(i), named=True)
            say(f"    {sc[i]:.3f} {r['kind'][:12]:12s} {r['agent'][:18] if r['agent'] else '-':18s} {r['text'][:170].replace(chr(10),' ')!r}")
    del m; torch.mps.empty_cache()
