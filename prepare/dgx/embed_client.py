"""Embed texts through an OpenAI-compatible vLLM /v1/embeddings server, with an on-disk cache.
embed(texts, tag, name) -> float32 unit rows; cached at results/emb_cache/<tag>/<name>.npy (float16) with a text hash."""

import hashlib
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

URL = os.environ.get("EMB_URL", "http://localhost:8100/v1/embeddings")


def _post(batch, trunc):
    body = json.dumps(
        {"model": "emb", "input": batch, "truncate_prompt_tokens": trunc}
    ).encode()
    for attempt in range(5):
        try:
            r = json.load(
                urllib.request.urlopen(
                    urllib.request.Request(
                        URL, body, {"Content-Type": "application/json"}
                    ),
                    timeout=600,
                )
            )
            return [
                d["embedding"] for d in sorted(r["data"], key=lambda d: d["index"])
            ], r.get("usage", {}).get("prompt_tokens", 0)
        except Exception:
            if attempt == 4:
                raise
            time.sleep(3 * (attempt + 1))


def embed(texts, tag, name, bs=32, workers=8, trunc=2000, verbose=True):
    h = hashlib.sha1("\x00".join(texts).encode()).hexdigest()[:12]
    d = f"results/emb_cache/{tag}"
    os.makedirs(d, exist_ok=True)
    p = f"{d}/{name}-{h}.npy"
    if os.path.exists(p):
        if verbose:
            print(f"  cache hit {p}")
        return np.load(p).astype(np.float32)
    order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
    batches = [order[i : i + bs] for i in range(0, len(order), bs)]
    out = [None] * len(texts)
    ntok = 0
    t0 = time.time()
    with ThreadPoolExecutor(workers) as ex:
        for idx, (vecs, nt) in zip(
            batches, ex.map(lambda b: _post([texts[i] for i in b], trunc), batches)
        ):
            for i, v in zip(idx, vecs):
                out[i] = v
            ntok += nt
    dt = time.time() - t0
    E = np.asarray(out, dtype=np.float32)
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    np.save(p, E.astype(np.float16))
    if verbose:
        print(
            f"  {tag}/{name}: {len(texts)} texts, {ntok} tokens in {dt:.0f}s = {len(texts) / dt:.1f} texts/s, {ntok / dt:.0f} tok/s -> {p}"
        )
    return E
