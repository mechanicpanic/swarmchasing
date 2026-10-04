# Per-agent rates (% of messages) of style features, chat and thought.
import polars as pl
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(400)
ORDER = ["Claude 3.5 Sonnet","Claude 3.7 Sonnet","Claude Sonnet 4.5","Claude Sonnet 4.6","Claude Sonnet 5",
 "Claude Opus 4","Claude Opus 4.1","Claude Opus 4.5","Opus 4.5 (Claude Code)","Claude Opus 4.6","Claude Opus 4.7","Claude Opus 4.8","Claude Opus 5",
 "Claude Haiku 4.5","Claude Fable 5","Claude Fable 5.1",
 "GPT-4o","GPT-4.1","o1","o3","o4-mini","GPT-5","GPT-5.1","GPT-5.2","GPT-5.4","GPT-5.5","GPT-5.6 Sol","GPT-6 Astra",
 "Gemini 2.5 Pro","Gemini 3 Pro","Gemini 3.1 Pro","Gemini 3.5 Flash","Gemini 3.8 Flash",
 "DeepSeek-V3.2","DeepSeek-V4-Pro","Grok 4","Grok 4.5","Kimi K2.6","Kimi K3","GLM-5.2","GLM-5.3 Flash","Muse Spark 1.3"]
for src in ["chat","thought"]:
    s = pl.read_parquet(f"style_{src}.parquet")
    feats = [c for c in s.columns if c not in ("agent","day","len")]
    r = s.group_by("agent").agg(pl.len().alias("n"), pl.col("len").median().alias("medlen"),
                                *[(pl.col(f).mean()*100).round(1).alias(f) for f in feats])
    r = r.filter(pl.col("agent").is_in(ORDER)).with_columns(pl.col("agent").replace_strict({a:i for i,a in enumerate(ORDER)}, default=99).alias("o")).sort("o").drop("o")
    r.write_csv(f"style_rates_{src}.csv")
    print(src); print(r)
