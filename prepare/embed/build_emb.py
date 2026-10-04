"""village_noemb.parquet (written by prismql ingest) -> village.parquet with `emb` = embeddinggemma-300m vectors of `text`,
documents encoded with the retrieval doc prompt through the vLLM server on :8100, in row order; blank text -> zero vector.
Stamps the same schema metadata prismql.ingest.core.write would."""

import sys
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, "runs")
from embed_client import embed

MODEL, DOC, QUERY = (
    "google/embeddinggemma-300m",
    "title: none | text: ",
    "task: search result | query: ",
)
t = pq.read_table("village_noemb.parquet")
n = t.num_rows
text = t.column("text").to_pylist()
idx = [i for i, s in enumerate(text) if s is not None and s.strip() != ""]
print(f"{n} rows, {len(idx)} with text", flush=True)
t0 = time.time()
E = embed(
    [DOC + text[i] for i in idx], "gemma", "village_full", trunc=2048, workers=8, bs=32
)
print(f"encoded in {time.time() - t0:.0f}s", flush=True)
M = np.zeros((n, E.shape[1]), dtype=np.float32)
M[idx] = E
emb = pa.FixedSizeListArray.from_arrays(
    pa.array(M.ravel(), type=pa.float32()), E.shape[1]
)
t = t.append_column("emb", emb)
meta = dict(t.schema.metadata or {})
meta.update(
    {
        b"prismql.embed_model": MODEL.encode(),
        b"prismql.embed_text": b"text",
        b"prismql.embed_doc_prompt": DOC.encode(),
        b"prismql.embed_query_prompt": QUERY.encode(),
    }
)
pq.write_table(t.replace_schema_metadata(meta), "village.parquet")
print("wrote village.parquet", t.num_rows, "rows, emb", E.shape[1], flush=True)
