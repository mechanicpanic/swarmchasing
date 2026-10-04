# Stage 1b: Title-Case multi-word names (2-4 words) from raw agent chat, agent names/URLs/markdown removed.
import polars as pl, re
C = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/"
chat = pl.read_parquet(C+"chat_raw.parquet", columns=["id","time","kind","agent","text"])
agents = sorted(chat.filter(pl.col("kind")=="agent")["agent"].unique().to_list(), key=len, reverse=True)
alts = [re.escape(a) for a in agents]
short=set()
for n in agents:
    m = re.match(r"(?:Claude )?(Opus|Sonnet|Haiku|Fable) (\d(?:\.\d)?)", n)
    if m: short.add(f"{m.group(1)} {m.group(2)}")
    for fam in ["Gemini","GPT","Claude","DeepSeek","Grok","Kimi","GLM","Qwen","Llama","Muse","Mistral"]:
        pass
alts += [re.escape(s) for s in sorted(short, key=len, reverse=True)]
name_re = "@?(?:" + "|".join(alts) + r")"
txt = (pl.col("text").str.replace_all(r"https?://\S+|\S+@\S+\.\S+|`[^`]*`", " ¶ ")
       .str.replace_all(name_re, " ¶ ").str.replace_all(r"[‑‐]", "-"))
# a Title-Case run of 2-4 words, not at a sentence start (preceded by a lowercase word or comma/quote/colon)
rx = r"(?:[a-z,;:\"“(]|\*\*) +((?:[A-Z][a-z]+|[A-Z]{2,})(?:[ \-](?:of |the |and |de )?(?:[A-Z][a-z]+|[A-Z]{2,})){1,3})\b"
d = (chat.filter(pl.col("text").is_not_null()).with_columns(txt.alias("t"))
     .with_columns(pl.col("t").str.extract_all(rx).alias("g")).explode("g").drop_nulls("g")
     .with_columns(pl.col("g").str.replace(r"^(?:[a-z,;:\"“(]|\*\*) +", "").alias("g"))
     .unique(["id","g"]))
d = d.with_columns(pl.col("g").str.to_lowercase().str.replace_all("-", " ").alias("key"))
ag = d.filter(pl.col("kind")=="agent")
hum = d.filter(pl.col("kind")=="user").group_by("key").agg(pl.col("time").min().alias("human_first"))
fa = ag.group_by("key","agent").agg(pl.col("time").min().alias("t0"))
s = (fa.sort("t0").group_by("key").agg(pl.col("t0").first().alias("first"), pl.col("agent").first().alias("origin"),
        pl.len().alias("n_agents"), pl.col("t0").sort().alias("ts")).filter(pl.col("n_agents")>=4)
     .with_columns(((pl.col("ts").list.get(3)-pl.col("first")).dt.total_hours()/24).alias("days_to_4")).drop("ts")
     .join(ag.group_by("key").agg(pl.len().alias("uses"), pl.col("g").mode().first().alias("form")), on="key")
     .join(hum, on="key", how="left"))
s.write_parquet("title_stage1.parquet")
print(s.height); pl.Config.set_tbl_rows(80); pl.Config.set_fmt_str_lengths(40)
print(s.sort("n_agents", descending=True).select("form","first","origin","n_agents","uses","days_to_4","human_first").head(80))
