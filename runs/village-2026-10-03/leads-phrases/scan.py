# Stage 3: one Aho-Corasick pass over chat and memory diffs for all pool keys.
# Text normalised like the keys: URLs/emails/code spans/agent names removed, lowercase, non-alnum -> space.
import polars as pl, re, ahocorasick, gc
C = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/"
P = pl.read_parquet("pool.parquet")
FAM = {"claude","sonnet","opus","haiku","gemini","gpt","grok","kimi","glm","qwen","llama","deepseek","fable","muse","o3","o1","mistral","flash","pro"}
P = P.filter(pl.col("key").map_elements(lambda k: not any(w in FAM for w in k.split()), return_dtype=pl.Boolean)).with_row_index("cid")
P.write_parquet("pool_scan.parquet"); print("pool", P.height)
A = ahocorasick.Automaton()
for cid, k in zip(P["cid"].to_list(), P["key"].to_list()): A.add_word(" "+k+" ", cid)
A.make_automaton()
chat = pl.read_parquet(C+"chat_raw.parquet", columns=["id","time","kind","agent","room","lab"]).sort("time")
agents = sorted(chat.filter(pl.col("kind")=="agent")["agent"].unique().to_list(), key=len, reverse=True)
name_re = "(?i)@?(?:" + "|".join(re.escape(a) for a in agents) + ")"
def norm(col):
    return (pl.lit(" ") + col.str.replace_all(r"https?://\S+|\S+@\S+\.\S+|`[^`]*`", " ").str.replace_all(name_re, " ")
            .str.to_lowercase().str.replace_all(r"[^a-z0-9']+", " ") + pl.lit(" "))
def scan(texts):
    out = []
    for j, s in enumerate(texts):
        if s is None: continue
        seen = set()
        for _, cid in A.iter(s):
            if cid not in seen: seen.add(cid); out.append((j, cid))
    return out
# chat
ct = pl.read_parquet(C+"chat_raw.parquet", columns=["id","text"])
order = chat.select("id").with_row_index("i")
ct = order.join(ct, on="id", how="left").sort("i")
nt = ct.select(norm(pl.col("text")).alias("t"))["t"].to_list()
h = scan(nt); del nt, ct; gc.collect()
hits = pl.DataFrame(h, schema=["i","cid"], orient="row").with_columns(pl.col("i").cast(pl.UInt32), pl.col("cid").cast(pl.UInt32))
chat.with_row_index("i").write_parquet("chat_index.parquet")
hits.write_parquet("chat_hits.parquet"); print("chat hits", hits.height, flush=True)
# memory diffs (added lines), chunked
mem = pl.scan_parquet(C+"village_raw.parquet").filter(pl.col("kind")=="memory").select("time","agent","text")
nrow = mem.select(pl.len()).collect().item(); CH = 15000; aggs = []
for s in range(0, nrow, CH):
    d = mem.slice(s, CH).collect()
    hh = scan(d.select(norm(pl.col("text")).alias("t"))["t"].to_list())
    if hh:
        x = pl.DataFrame(hh, schema=["j","cid"], orient="row").join(d.select("time","agent").with_row_index("j").with_columns(pl.col("j").cast(pl.Int64)), on="j")
        aggs.append(x.group_by("cid","agent").agg(pl.col("time").min().alias("m_first"), pl.col("time").max().alias("m_last"), pl.len().alias("m_n")))
    del d; gc.collect(); print("mem", s, flush=True)
M = pl.concat(aggs).group_by("cid","agent").agg(pl.col("m_first").min(), pl.col("m_last").max(), pl.col("m_n").sum())
M.write_parquet("mem_hits.parquet"); print("mem rows", M.height)
