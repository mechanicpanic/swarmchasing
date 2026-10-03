# Lineage tables: candidate rate per 1k msgs (chat / thought) by model, in release order.
import sys, polars as pl
LIN = {
 "Claude Opus": ["Claude Opus 4","Claude Opus 4.1","Claude Opus 4.5","Claude Opus 4.6","Claude Opus 4.7","Claude Opus 4.8","Claude Opus 5"],
 "Claude Sonnet": ["Claude 3.5 Sonnet","Claude 3.7 Sonnet","Claude Sonnet 4.5","Claude Sonnet 4.6","Claude Sonnet 5"],
 "Claude other": ["Claude Haiku 4.5","Claude Fable 5","Claude Fable 5.1"],
 "OpenAI": ["GPT-4o","GPT-4.1","o1","o3","o4-mini","GPT-5","GPT-5.1","GPT-5.2","GPT-5.4","GPT-5.5","GPT-5.6 (3 agents)","GPT-6 Astra"],
 "Gemini": ["Gemini 2.5 Pro","Gemini 3 Pro","Gemini 3.1 Pro","Gemini 3.5 Flash","Gemini 3.8 Flash"],
 "Others": ["DeepSeek-V3.2 (pre-swap)","DeepSeek (post-swap, likely V4-Flash)","DeepSeek-V4-Pro","Grok 4","Grok 4.5","Kimi K2.6","Kimi K3","GLM-5.2","GLM-5.3 Flash","Muse Spark 1.3"],
}
ORDER = [a for v in LIN.values() for a in v]
src = sys.argv[1] if len(sys.argv) > 1 else "chat"
val = sys.argv[2] if len(sys.argv) > 2 else "rate"
r = pl.read_parquet("cand_rates_long.parquet").filter(pl.col("src") == src)
r = r.with_columns(pl.when(pl.col("agent").str.starts_with("GPT-5.6")).then(pl.lit("GPT-5.6 (3 agents)")).otherwise(pl.col("agent")).alias("agent"))
r = r.group_by("cand","agent").agg(pl.col("n").sum(), pl.col("y").sum(), pl.col("exp").sum())
r = r.with_columns(rate=1000*pl.col("y")/pl.col("n"), oe=(pl.col("y")+0.5)/(pl.col("exp")+0.5))
r = r.filter(pl.col("agent").is_in(ORDER) & (pl.col("n") >= 50))
w = r.pivot(on="agent", index="cand", values=val)
cols = ["cand"] + [a for a in ORDER if a in w.columns]
w = w.select(cols)
w.write_csv(f"lineage_{src}_{val}.csv")
ab = lambda a: a.replace("Claude ","").replace("Gemini ","Gm").replace("DeepSeek-V3.2 (pre-swap)","DS3.2pre").replace("DeepSeek (post-swap, likely V4-Flash)","DSpostSw").replace("DeepSeek-","DS").replace(" (3 agents)","*").replace(" Flash","F").replace(" Pro","P").replace("Sonnet","Son").replace("Spark ","")[:8]
print("cand".ljust(34) + "".join(ab(c).rjust(8) for c in cols[1:]))
for row in w.iter_rows():
    print(row[0][:34].ljust(34) + "".join((f"{v:8.1f}" if v is not None else "       -") for v in row[1:]))
