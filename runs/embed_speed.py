"""Tokens/s for Qwen3-Embedding-0.6B variants on 400 real THOUGHT texts (length-sorted batches, max 512 tokens)."""
import time, polars as pl
docs = pl.read_parquet('data/village_events.parquet', columns=['kind','text']).filter(pl.col('kind')=='THOUGHT').sample(400, seed=7)['text'].to_list()
def batches(tok, bs):
    order = sorted(docs, key=len)
    return [order[i:i+bs] for i in range(0, len(order), bs)]
import mlx.core as mx
from mlx_embeddings.utils import load
for name in ["mlx-community/Qwen3-Embedding-0.6B-8bit", "mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ", "mlx-community/Qwen3-Embedding-0.6B-mxfp8", "Qwen/Qwen3-Embedding-0.6B"]:
    try: model, tok = load(name)
    except Exception as e: print(name, 'LOAD FAILED', str(e)[:150]); continue
    tok = getattr(tok, '_tokenizer', tok)
    for bs in (8, 32):
        ntok = 0; t0 = time.time()
        for b in batches(tok, bs):
            enc = tok(b, return_tensors='np', padding=True, truncation=True, max_length=512)
            ntok += int(enc['attention_mask'].sum())
            o = model(input_ids=mx.array(enc['input_ids']), attention_mask=mx.array(enc['attention_mask'])); mx.eval(o.text_embeds)
        dt = time.time() - t0; print(f"MLX {name:45s} bs={bs:2d}  {len(docs)/dt:6.1f} docs/s  {ntok/dt:7.0f} tok/s", flush=True)
    del model
import torch
from sentence_transformers import SentenceTransformer
for dtype in (torch.float16, torch.float32):
    m = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B", device='mps', model_kwargs={"torch_dtype": dtype}); m.max_seq_length = 512
    for bs in (8, 32):
        t0 = time.time(); m.encode(sorted(docs, key=len), batch_size=bs); dt = time.time() - t0
        print(f"ST  Qwen/Qwen3-Embedding-0.6B {str(dtype):15s} bs={bs:2d}  {len(docs)/dt:6.1f} docs/s", flush=True)
    del m; torch.mps.empty_cache()
