# ruff: noqa: F821  -- names come from exec() of embed_bench.py (sample, questions); exploratory script
"""Same sample, questions and output as runs/embed_bench.py, but inference through MLX (mlx-embeddings) with
mlx-community conversions. Docs are encoded length-sorted so a batch pads little. usage: python runs/embed_bench_mlx.py [name-filter...]"""
import sys, time, numpy as np, mlx.core as mx
from mlx_embeddings.utils import load
exec(open('runs/embed_bench.py').read().split('# (name,')[0].split('from sentence_transformers')[0].replace('import time, sys, numpy as np, polars as pl, torch', ''))
exec('\n'.join(l for l in open('runs/embed_bench.py').read().splitlines() if l.startswith(('df =', 'S =', '               df.', 'docs =', 'Q =', '     "'))))
QWEN = "Instruct: Given a description of what an AI agent is thinking or doing, retrieve the agent thoughts and messages that express it\nQuery: "
M = [("Qwen/Qwen3-Embedding-0.6B", QWEN, ""),
     ("mlx-community/Qwen3-Embedding-0.6B-8bit", QWEN, ""),
     ("mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ", QWEN, ""),
     ("mlx-community/embeddinggemma-300m-bf16", "task: search result | query: ", "title: none | text: "),
     ("mlx-community/bge-small-en-v1.5-bf16", "Represent this sentence for searching relevant passages: ", ""),
     ("mlx-community/snowflake-arctic-embed-l-v2.0-8bit", "query: ", "")]
only = sys.argv[1:]
N = int(__import__('os').environ.get('N', len(docs)))
D_docs = docs[:N]
out = open('results/embed_bench.txt', 'a')
def say(*a):
    print(*a); print(*a, file=out); out.flush()
def enc(model, tok, texts, bs=8):
    order = sorted(range(len(texts)), key=lambda i: len(texts[i])); res = [None]*len(texts)
    for s in range(0, len(texts), bs):
        idx = order[s:s+bs]
        o = model(**{k: mx.array(v) for k, v in tok([texts[i] for i in idx], return_tensors='np', padding=True, truncation=True, max_length=512).items() if k in ('input_ids','attention_mask')} | {})
        e = np.array(o.text_embeds.astype(mx.float32)); 
        for j, i in enumerate(idx): res[i] = e[j]
    E = np.stack(res); return E / np.linalg.norm(E, axis=1, keepdims=True)
for name, qp, dp in M:
    if only and not any(x in name for x in only): continue
    try: model, tok = load(name)
    except Exception as e: say(f"\n##### {name}: LOAD FAILED {type(e).__name__}: {str(e)[:200]}"); continue
    tok = getattr(tok, '_tokenizer', tok)
    t0 = time.time(); D = enc(model, tok, [dp + d for d in D_docs]); dt = time.time() - t0
    qs = enc(model, tok, [qp + q for q in Q])
    say(f"\n##### MLX {name}  dim={D.shape[1]} max_seq=512  encode {len(D_docs)} docs in {dt:.0f}s = {len(D_docs)/dt:.0f}/s  -> full 570k stream ≈ {569540/(len(D_docs)/dt)/60:.0f} min")
    for q, qv in zip(Q, qs):
        sc = D @ qv; top = np.argsort(-sc)[:5]; say(f"  Q: {q}")
        for i in top:
            r = S.row(int(i), named=True)
            say(f"    {sc[i]:.3f} {r['kind'][:12]:12s} {r['agent'][:18] if r['agent'] else '-':18s} {r['text'][:170].replace(chr(10),' ')!r}")
    del model
