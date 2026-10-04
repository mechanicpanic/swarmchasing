# Stage 1a: lowercase 2-4-gram candidates from the tics thread's per-(agent,day,gram) counts.
# (Agent chat only, exact self-duplicates dropped, agent names -> "agentx", URLs -> urlx; df>=15.)
import polars as pl
from wordfreq import zipf_frequency as Z
T = "/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/tics/"
voc = pl.read_parquet(T+"ng_chat_vocab.parquet").filter(pl.col("n").is_between(2,4))
bad = r"\b(agentx|urlx|emailx)\b|\b\d+\b"
voc = voc.filter(~pl.col("g").str.contains(bad))
STOP = set("""a an the and or but of to in on at for with by from as is are was were be been it its this that these those i you we they he she
my your our their me us them not no yes so if then than too very just also all any some each every more most can will would should could
do does did have has had i'm it's we're you're i've let's there here what which who how when where why up out about into over after before
s t re ve ll d m don didn doesn isn aren wasn won can't don't i'll we'll you'll that's there's what's let""".split())
voc = voc.with_columns(pl.col("g").str.split(" ").alias("w"))
voc = voc.filter(~pl.col("w").list.first().is_in(list(STOP)) & ~pl.col("w").list.last().is_in(list(STOP)))
toks = sorted(set(t for ws in voc["w"].to_list() for t in ws))
zf = {t: Z(t.replace("-", " ") if "-" in t else t, "en") for t in toks}
voc = voc.with_columns(pl.col("w").map_elements(lambda ws: min(zf[t] for t in ws), return_dtype=pl.Float64).alias("min_zipf"),
                       pl.col("w").map_elements(lambda ws: any("-" in t for t in ws), return_dtype=pl.Boolean).alias("hyph"))
print("vocab after filters", voc.height)
c = pl.scan_parquet(T+"ng_chat_counts.parquet").join(voc.lazy().select("h"), on="h", how="semi")
fa = c.group_by("h","agent").agg(pl.col("day").min().alias("d0"), pl.col("c").sum().alias("c")).collect()
s = (fa.sort("d0").group_by("h").agg(pl.col("d0").first().alias("first_day"), pl.col("agent").first().alias("origin_day_agent"),
        pl.len().alias("n_agents"), pl.col("c").sum().alias("uses"), pl.col("d0").sort().alias("ds"))
     .filter(pl.col("n_agents")>=4)
     .with_columns((pl.col("ds").list.get(3)-pl.col("first_day")).dt.total_days().alias("days_to_4"))
     .drop("ds").join(voc.select("h","g","n","min_zipf","hyph"), on="h"))
s.write_parquet("ngram_stage1.parquet")
print(s.height)
print(s.filter(pl.col("min_zipf")<3.0).sort("n_agents", descending=True).head(40))
