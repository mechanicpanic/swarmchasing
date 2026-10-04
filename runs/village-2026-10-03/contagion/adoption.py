# Adoption (first use) vs exposure, and spontaneous use. Discriminates village-spread from trained-in.
import polars as pl
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(250); pl.Config.set_fmt_str_lengths(40)
F = pl.concat([pl.read_parquet("first_use.parquet"), pl.read_parquet("first_use_tics.parquet").with_columns(pl.col("phrase")+" [tics]")], how="diagonal_relaxed")
M = pl.read_csv("../models-table/models.csv").select(pl.col("agent_name").alias("agent"), "knowledge_cutoff")
M = M.with_columns(pl.col("knowledge_cutoff").str.slice(0,7).alias("cut_ym"))
F = F.join(M, on="agent", how="left")
ad = F.filter(pl.col("first_use").is_not_null() & (pl.col("agent")!=pl.col("origin")))
ad = ad.with_columns((pl.col("prior_uses_since_arrival")==0).alias("indep"),
                     (pl.col("cut_ym") < pl.col("global_first").dt.strftime("%Y-%m")).alias("cutoff_before_debut"))
def summ(d):
    e = d.filter(pl.col("pre_exp_rate").is_not_null())
    return dict(adopters=d.height,
        indep_pct=round(100*d["indep"].mean(),1),
        exposed1h_pct=round(100*d["exposed_1h_same_room"].mean(),1),
        OE=round(e["exposed_1h_same_room"].sum()/max(e["pre_exp_rate"].sum(),1e-9),2),
        med_h_since_last_other=round(d["hours_since_last_other"].median(),2),
        at_pct=round(100*d["at_exposed"].mean(),1),
        hum_pct=round(100*d["humrec_at_first"].mean(),1))
rows=[]
for (k,), d in ad.group_by("pkind"): rows.append(dict(kind=k, **summ(d)))
print(pl.DataFrame(rows))
rows=[]
for (p,k), d in ad.group_by("phrase","pkind"): rows.append(dict(phrase=p, kind=k, **summ(d)))
per = pl.DataFrame(rows).sort("kind","indep_pct"); per.write_csv("adoption_by_phrase.csv"); print(per)
print("coinage adopters with no exposure since arrival:")
print(ad.filter((pl.col("pkind")=="coinage") & pl.col("indep")).select("phrase","agent","arrive","first_use","global_first","origin","hours_since_last_other"))
print("independent (no-exposure) tic adoptions whose model cutoff predates the phrase's village debut:")
ti = ad.filter(pl.col("pkind").is_in(["tic"]) & pl.col("indep"))
print(ti.group_by("cutoff_before_debut").len())
ad.write_parquet("adoptions.parquet")
