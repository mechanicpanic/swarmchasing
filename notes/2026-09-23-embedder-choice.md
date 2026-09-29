# 2026-09-23 — choosing the embedder (run on the DGX Spark, vLLM v0.29 aarch64, container emb-vllm on :8100)

Code and caches on the DGX: `~/swarmchasing/runs/{embed_client,eval_actions,eval_paraphrase,sweep,sweep_para}.py|sh`,
vectors in `~/swarmchasing/results/emb_cache/<model>/`, MTEB table `~/swarmchasing/results/mteb_retrieval_eng_v2.csv`.

## MTEB(eng, v2), 10 retrieval tasks, only models reporting all 10
Qwen3-Embedding-8B 69.4 · 4B 68.5 · 0.6B 61.8 · snowflake-arctic-l-v2 58.6 · granite-english-r2 56.4 · bge-base 56.3 · embeddinggemma 55.7 · current paraphrase-multilingual-MiniLM 35.9.
Distrusted: inf-retriever (zero-shot 20%), Yuan/QZhou (little known).

## Our data: action-grounded eval
A THOUGHT is relevant to a query when the action it led to is the query's action. Pool 9,424 thoughts: all before REQUEST (156) / CANCEL (68) human helper,
300 each before SEARCH_HISTORY / PAUSE / START_USING_COMPUTER / CONSOLIDATE, 8,000 distractors before AGENT_TALK / STOP_USING_COMPUTER (WAIT excluded).
Six actions × five paraphrases; mean AP, 95% CI by bootstrap over queries. Random AP: 0.007–0.032.

| model | dim | mean AP | 95% CI | throughput on GB10 (tok/s) | full stream |
|---|---|---|---|---|---|
| granite-embedding-english-r2 | 768 | 0.187 | 0.143–0.238 | 149k | ~11 min |
| Qwen3-Embedding-0.6B | 1024 | 0.185 | 0.157–0.216 | 50k | ~35 min |
| Qwen3-Embedding-8B | 4096 | 0.165 | 0.142–0.192 | 5.2k | ~5.3 h |
| Qwen3-Embedding-8B @1024 | 1024 | 0.152 | 0.129–0.176 | | |
| bge-base-en-v1.5 | 768 | 0.154 | 0.116–0.199 | 213k | ~8 min |
| Qwen3-Embedding-4B | 2560 | 0.139 | 0.111–0.169 | 8.9k | ~3 h |

MTEB rank does not carry over: 8B and 4B are not better than 0.6B / granite on agent thoughts. CIs overlap; granite r2 and Qwen3-0.6B are the top pair.
START_USING_COMPUTER is hard for every model (AP ~0.06): its thoughts talk about the task, not about opening the computer.
Limits: one task type (decision intent in thoughts); queries written by us; no lexical baseline yet.

## Two modes (retrieval + symmetric), small models only — `results/eval_modes.txt`
Symmetric = each thought before one of the six actions as a query document, 10 nearest neighbours among OTHER agents' thoughts, purity = share leading to the same action.
Threshold study = per-query best-F1 threshold; spread in units of the pool's score sd; F1 when one global threshold is used for all 30 queries.

| model | tables | retrieval meanAP | thr IQR (sd) | F1 best → global | sym purity@10 (lift) |
|---|---|---|---|---|---|
| embeddinggemma-300m | 2 (retrieval doc prompt + similarity prompt) | 0.214 | 0.94 | 0.288 → 0.205 | 0.316 (14.4×) with its sym table; 0.274 doc-doc |
| Qwen3-Embedding-0.6B | 1 | 0.185 | 0.71 | 0.262 → 0.210 | 0.280 (14.7×) instructed; 0.241 doc-doc |
| granite-embedding-english-r2 | 1 | 0.187 | 1.47 | 0.264 → 0.180 | 0.272 (13.3×) doc-doc |
| Yuan-embedding-2.0-en | 1 | 0.132 | 0.78 | 0.204 → 0.164 | 0.203 (10.2×) instructed |

Yuan leads small models on MTEB retrieval (70.7) and is the worst here: its MTEB edge does not transfer to agent thoughts.
One global threshold costs 20–32% F1; Qwen3's scale is the most stable, granite's the least. `near` should not rely on one fixed θ for every question.

## Decision and build (2026-09-23)
Aleph chose embeddinggemma-300m (retrieval table only for now; the symmetric table waits for `near`, prismql #103).
`data/village.parquet` = `prismql ingest table data/village_events.parquet … --id id --time created_at --sort seq` (no embed) + `emb` from vLLM on the DGX
(`~/swarmchasing/runs/build_emb.py`): 486,812 texts, 107.7M tokens, 28 min; client-side limit 64k tok/s (8×32 in flight) vs 160k the server can do — use more workers next time.
Parity vLLM vs sentence-transformers on 20 texts: min cosine 0.9999 (docs, "title: none | text: "), 1.0000 (queries, "task: search result | query: ").
Metadata stamped as prismql.ingest.core.write does. Previous file kept as `data/village.pre-gemma.parquet` (381k rows, no THOUGHT, MiniLM).
