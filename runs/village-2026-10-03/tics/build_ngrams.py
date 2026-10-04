# Build per-(agent, day, gram) document counts for 1..5-grams.
# Usage: build_ngrams.py chat|thought
# Memory-conscious: two passes over chunks, grams identified by u64 hash.
#   pass 1: global document frequency per hash -> keep df >= MIN_DF
#   pass 2: (agent, day, hash) doc counts for kept hashes + hash->text vocab
# Docs: agent chat messages (chat_raw, kind=agent) or THOUGHT rows from
# village_full (deduped on text). Exact duplicate texts from the same agent
# are dropped (templated reposts would otherwise dominate).
# Agent names in text are replaced by the token "agentx" so that e.g.
# "thanks @GPT-5" and "thanks @o3" count as the same gram.
import sys, re, polars as pl

SRC = sys.argv[1]
OUT = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/tics/"
CORP = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/"
MIN_DF = 15
import os
CHUNK = int(os.environ.get("CHUNK", 4000))
P = int(os.environ.get("P", 4))

chat = pl.read_parquet(CORP + "chat_raw.parquet", columns=["agent", "kind"])
agents = sorted(chat.filter(pl.col("kind") == "agent")["agent"].unique().to_list())
del chat

if SRC == "chat":
    d = (pl.read_parquet(CORP + "chat_raw.parquet", columns=["id", "time", "kind", "agent", "text"])
         .filter(pl.col("kind") == "agent").drop("kind"))
else:
    d = (pl.scan_parquet(CORP + "../village_embeddings_2026-09-29/3_village_full_with_text.parquet")
         .filter(pl.col("kind") == "THOUGHT").select("id", "time", "agent", "text").collect()
         .with_columns(pl.col("time").dt.replace_time_zone(None)))
d = (d.filter(pl.col("text").is_not_null()).sort("time")
     .unique(["agent", "text"], keep="first", maintain_order=True)
     .with_columns(pl.col("time").dt.date().alias("day")))
SAMPLE = int(os.environ.get("SAMPLE", 0))  # cap docs per agent (random sample) to bound cost
if SAMPLE:
    d = (d.with_columns(pl.int_range(pl.len()).shuffle(seed=1).over("agent").alias("_r"))
         .filter(pl.col("_r") < SAMPLE).drop("_r").sort("time"))
MAXN = int(os.environ.get("MAXN", 5))

# name patterns, longest first; also bare short forms like "opus 4.5", "sonnet 4.5", "gemini 3"
names = sorted(set(agents), key=len, reverse=True)
alts = [re.escape(n.lower()) for n in names]
short = set()
for n in names:
    m = re.match(r"(?:claude )?(opus|sonnet|haiku|fable) (\d(?:\.\d)?)", n.lower())
    if m: short.add(f"{m.group(1)} {m.group(2)}")
alts += [re.escape(s) for s in sorted(short, key=len, reverse=True)]
name_re = "@?(?:" + "|".join(alts) + r")(?:'s)?"

def norm(col):
    return (col.str.to_lowercase()
            .str.replace_all("‑|‐|‒|–", "-")
            .str.replace_all("[‘’]", "'")
            .str.replace_all(r"https?://\S+", " urlx ")
            .str.replace_all(r"\S+@\S+\.\S+", " emailx ")
            .str.replace_all(name_re, " agentx ")
            .str.extract_all(r"[a-z0-9]+(?:['\-][a-z0-9]+)*"))

def grams(chunk, part=None):
    w = chunk.select("id", "agent", "day", norm(pl.col("text")).alias("w"))
    outs = []
    for n in range(1, MAXN + 1):
        g = (w.filter(pl.col("w").list.len() >= n)
             .with_columns(pl.int_ranges(0, pl.col("w").list.len() - n + 1).alias("i"))
             .explode("i")
             .with_columns(pl.concat_str([pl.col("w").list.get(pl.col("i") + k) for k in range(n)],
                                         separator=" ").alias("g"))
             .select("id", "agent", "day", "g")
             .with_columns(pl.col("g").hash(seed=7).alias("h"), pl.lit(n, pl.UInt8).alias("n")))
        if part is not None:
            g = g.filter(pl.col("h") % P == part).select("id", "h")
        g = g.unique(["id", "h"])
        outs.append(g)
    return pl.concat(outs)

N = d.height
# pass 1
keeps = []
for part in range(P):
    df = None
    for s in range(0, N, CHUNK):
        g = grams(d.slice(s, CHUNK), part).group_by("h").agg(pl.len().alias("df"))
        df = g if df is None else pl.concat([df, g]).group_by("h").agg(pl.col("df").sum())
    print("pass1 part", part, df.height, flush=True)
    keeps.append(df.filter(pl.col("df") >= MIN_DF).select("h"))
    del df
keep = pl.concat(keeps)
print("kept", keep.height, flush=True)
# pass 2
parts, vocab = [], []
for s in range(0, N, CHUNK):
    g = grams(d.slice(s, CHUNK)).join(keep, on="h", how="semi")
    parts.append(g.group_by("agent", "day", "h").agg(pl.len().alias("c").cast(pl.UInt32)))
    vocab.append(g.select("h", "g", "n").unique("h"))
    print("pass2", s, flush=True)
counts = pl.concat(parts).group_by("agent", "day", "h").agg(pl.col("c").sum())
voc = pl.concat(vocab).unique("h")
docs = d.group_by("agent", "day").agg(pl.len().alias("docs"))
counts.write_parquet(OUT + f"ng_{SRC}_counts.parquet")
voc.write_parquet(OUT + f"ng_{SRC}_vocab.parquet")
docs.write_parquet(OUT + f"ng_{SRC}_docs.parquet")
print(counts.height, voc.height, docs["docs"].sum())
