"""Action-grounded retrieval eval: a THOUGHT is relevant to a query when the action it led to (`of`) is that query's action.
Pool = every THOUGHT of the three target actions + 8000 random other THOUGHTs. Metric per query: average precision and recall@100.
usage: python runs/embed_eval_actions.py [name-filter...]  -> appends to results/embed_eval_actions.txt"""
import sys, time, numpy as np, polars as pl
th = pl.read_parquet('data/village_events.parquet', columns=['kind','of','text']).filter(pl.col('kind')=='THOUGHT')
T = {"REQUEST_HUMAN_HELPER": "I am stuck on something only a person can do, so I will ask a human helper to do it for me.",
     "CANCEL_REQUEST_FOR_HUMAN_HELPER": "I no longer need the human helper, so I will cancel my request for help.",
     "SEARCH_HISTORY": "I don't remember what happened earlier, so I will search the village history to find out."}
pos = th.filter(pl.col('of').is_in(list(T)))
pos = pl.concat([pos.filter(pl.col('of')!='SEARCH_HISTORY'), pos.filter(pl.col('of')=='SEARCH_HISTORY').sample(300, seed=3)])
pool = pl.concat([pos, th.filter(~pl.col('of').is_in(list(T))).sample(8000, seed=3)])
docs, of = pool['text'].to_list(), pool['of'].to_list()
QWEN = "Instruct: Given a description of what an AI agent is thinking or doing, retrieve the agent thoughts that express it\nQuery: "
M = [("st", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "", "", None, {}),
     ("st", "BAAI/bge-small-en-v1.5", "Represent this sentence for searching relevant passages: ", "", None, {}),
     ("st", "BAAI/bge-base-en-v1.5", "Represent this sentence for searching relevant passages: ", "", None, {}),
     ("st", "ibm-granite/granite-embedding-small-english-r2", "", "", None, {}),
     ("st", "ibm-granite/granite-embedding-english-r2", "", "", None, {}),
     ("st", "Snowflake/snowflake-arctic-embed-l-v2.0", "", "", "query", {}),
     ("st", "google/embeddinggemma-300m", "task: search result | query: ", "title: none | text: ", None, {}),
     ("mlx", "Qwen/Qwen3-Embedding-0.6B", QWEN, "", None, {})]
only = sys.argv[1:]; out = open('results/embed_eval_actions.txt', 'a')
def say(s): print(s, flush=True); print(s, file=out); out.flush()
def ap(scores, rel):
    o = np.argsort(-scores); r = rel[o]; hits = np.cumsum(r); prec = hits / np.arange(1, len(r)+1)
    return float((prec * r).sum() / r.sum()), float(r[:100].sum() / r.sum())
for backend, name, qp, dp, pn, kw in M:
    if only and not any(x in name for x in only): continue
    t0 = time.time()
    if backend == "st":
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer(name, device='mps', **kw); m.max_seq_length = 128 if 'MiniLM' in name else 512
        D = m.encode([dp+d for d in docs], batch_size=32, normalize_embeddings=True)
        Qv = m.encode(list(T.values()), prompt_name=pn, normalize_embeddings=True) if pn else m.encode([qp+q for q in T.values()], normalize_embeddings=True)
    else:
        import mlx.core as mx
        from mlx_embeddings.utils import load
        model, tok = load(name); tok = getattr(tok, '_tokenizer', tok)
        def enc(texts, bs=8):
            order = sorted(range(len(texts)), key=lambda i: len(texts[i])); res = [None]*len(texts)
            for s in range(0, len(texts), bs):
                idx = order[s:s+bs]; e = tok([texts[i] for i in idx], return_tensors='np', padding=True, truncation=True, max_length=512)
                v = np.array(model(input_ids=mx.array(e['input_ids']), attention_mask=mx.array(e['attention_mask'])).text_embeds.astype(mx.float32))
                for j, i in enumerate(idx): res[i] = v[j]
            E = np.stack(res); return E / np.linalg.norm(E, axis=1, keepdims=True)
        D = enc([dp+d for d in docs]); Qv = enc([qp+q for q in T.values()])
    dt = time.time() - t0
    row = [f"{name.split('/')[-1]:42s} {len(docs)/dt:5.0f} docs/s"]
    aps = []
    for (act, _), qv in zip(T.items(), Qv):
        rel = np.array([o == act for o in of], dtype=float); a, r100 = ap(D @ qv, rel); aps.append(a)
        row.append(f"{act[:14]:14s} AP {a:.3f} R@100 {r100:.2f}")
    say(" | ".join(row) + f" | mean AP {np.mean(aps):.3f}")
