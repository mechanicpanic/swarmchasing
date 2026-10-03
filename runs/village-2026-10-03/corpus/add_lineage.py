# Adds lab, family and cohort (half-year the model joined the village; a
# stand-in for release date) to the chat and village streams.
import polars as pl
from pathlib import Path
C = Path(__file__).resolve().parent
LABS = [("Anthropic", r"Claude|Opus|Sonnet|Haiku|Fable"), ("OpenAI", r"GPT|^o[0-9]"),
        ("Google", r"Gemini"), ("DeepSeek", r"DeepSeek"), ("xAI", r"Grok"),
        ("Moonshot", r"Kimi"), ("Zhipu", r"GLM"), ("Meta", r"Muse")]
def lab():
    e = pl.lit("other")
    for name, rx in reversed(LABS):
        e = pl.when(pl.col("agent").str.contains(rx)).then(pl.lit(name)).otherwise(e)
    return pl.when(pl.col("agent") == "human").then(pl.lit("human")).otherwise(e)
def family():
    a = pl.col("agent")
    return (pl.when(a.str.contains("Opus")).then(pl.lit("Claude Opus"))
            .when(a.str.contains("Sonnet")).then(pl.lit("Claude Sonnet"))
            .when(a.str.contains("Haiku")).then(pl.lit("Claude Haiku"))
            .when(a.str.contains("Fable")).then(pl.lit("Claude Fable"))
            .when(a.str.contains(r"^o[0-9]")).then(pl.lit("OpenAI o-series"))
            .otherwise(a.str.extract(r"^([A-Za-z]+(?:-[A-Za-z]+)?)")))
chat = pl.read_parquet(C / "chat_raw.parquet", columns=["agent", "time", "kind"])
arrived = (chat.filter(pl.col("kind") == "agent").group_by("agent").agg(pl.col("time").min().alias("arrived"))
           .with_columns((pl.col("arrived").dt.year().cast(pl.Utf8) + pl.when(pl.col("arrived").dt.month() <= 6).then(pl.lit("H1")).otherwise(pl.lit("H2"))).alias("cohort"))
           .select("agent", "cohort"))
for name in ["chat_raw", "village_raw"]:
    df = pl.read_parquet(C / f"{name}.parquet")
    df = (df.drop([c for c in ("lab", "family", "cohort") if c in df.columns])
            .join(arrived, on="agent", how="left")
            .with_columns(lab().alias("lab"), family().alias("family"), pl.col("cohort").fill_null("human")))
    df.write_parquet(C / f"{name}.parquet")
    print(name, df.shape)
print(df.filter(pl.col("kind") != "user").group_by("lab", "cohort").agg(pl.col("agent").n_unique().alias("agents")).sort("cohort", "lab"))
