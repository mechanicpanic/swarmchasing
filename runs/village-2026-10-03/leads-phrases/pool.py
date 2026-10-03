# Stage 2: merge Title-Case and rare/hyphenated n-gram streams into one candidate pool (keys normalised).
import polars as pl, re
t = pl.read_parquet("title_stage1.parquet")
n = pl.read_parquet("ngram_stage1.parquet")
TECH = set("""md py js ts html css json yaml yml npm npx git github gitlab cdn api http https www org com io app url urls pdf csv png jpg svg
readme repo repos ssh cli bash sudo pip node localhost dns ssl tls oauth gmail google drive docs sheets doc sheet gdoc chrome firefox
substack twitter reddit youtube wikipedia linkedin discord slack netlify vercel surge glitch replit pages wordpress medium figma canva notion
openai anthropic deepmind xai deepseek meta microsoft apple amazon aws gcp azure owasp juice zoom lichess chess com txt ui ux id ids
sql db cron env config localtunnel loca lt tunnel ngrok cloudflare kaggle hugging huggingface arxiv paypal stripe gofundme justgiving
every org givewell malaria helen keller amazon etsy printful shopify teespring redbubble twitch tiktok instagram facebook bluesky mastodon
email emails inbox ok pr prs commit commits branch main merge issue issues""".split())
def keyify(s): return re.sub(r"\s+"," ", re.sub(r"[^a-z0-9']+"," ", s.lower())).strip()
T = (t.filter((pl.col("uses")>=8) & (pl.col("human_first").is_null() | (pl.col("human_first")>pl.col("first"))))
      .with_columns(pl.col("key").map_elements(keyify, return_dtype=pl.Utf8).alias("key"), pl.lit("title").alias("src"))
      .select("key","form","first","origin","n_agents","uses","src"))
N = (n.filter(((pl.col("min_zipf")<2.8)|pl.col("hyph")) & (pl.col("uses")>=10) & (pl.col("first_day")>=pl.date(2025,4,9)))
      .with_columns(pl.col("g").map_elements(keyify, return_dtype=pl.Utf8).alias("key"), pl.col("g").alias("form"),
                    pl.col("first_day").cast(pl.Datetime("us")).alias("first"), pl.col("origin_day_agent").alias("origin"), pl.lit("ngram").alias("src"))
      .select("key","form","first","origin","n_agents","uses","src"))
P = pl.concat([T, N]).sort("n_agents", descending=True).unique("key", keep="first")
P = P.filter(pl.col("key").map_elements(lambda k: not any(w in TECH for w in k.split()) and len(k)>=6 and len(k.split())>=2
                                        and not all(len(w)<=2 for w in k.split()), return_dtype=pl.Boolean))
# drop superstrings of another candidate (keep the shortest form; variants examined later as mutations)
keys = set(P["key"].to_list())
def has_sub(k):
    w = k.split()
    for i in range(len(w)):
        for j in range(i+2, len(w)+1):
            if (i,j)!=(0,len(w)) and " ".join(w[i:j]) in keys: return True
    return False
P = P.with_columns(pl.col("key").map_elements(has_sub, return_dtype=pl.Boolean).alias("sup")).filter(~pl.col("sup")).drop("sup")
P.write_parquet("pool.parquet")
print(P.height, P.group_by("src").len())
