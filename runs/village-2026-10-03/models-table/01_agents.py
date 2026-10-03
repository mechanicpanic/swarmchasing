import polars as pl, gzip, json
rows=[json.loads(l) for l in gzip.open('/Users/phosphorus/projects/prismql-data/ai-village/agents.jsonl.gz','rt')]
a=pl.DataFrame([{k:r[k] for k in ['name','model_string','created_at','input_tokens_used','output_tokens_used','is_participating']} for r in rows])
c=pl.scan_parquet('/Users/phosphorus/projects/prismql-data/ai-village/corpus/chat_raw.parquet').filter(pl.col('kind')=='agent').group_by('agent').agg(pl.col('time').min().alias('first_msg'),pl.col('time').max().alias('last_msg'),pl.len().alias('n_msgs'),pl.col('model').first(),pl.col('lab').first(),pl.col('family').first(),pl.col('cohort').first()).collect()
j=a.join(c,left_on='name',right_on='agent',how='full',coalesce=True).sort('created_at')
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_width_chars(300); pl.Config.set_fmt_str_lengths(60)
print(j)
j.write_parquet('/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/models-table/agents_times.parquet')
