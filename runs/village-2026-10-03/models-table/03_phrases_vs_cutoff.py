"""For a few phrases flagged in FIELD_NOTES as possibly trained-in, compare first village use (any agent)
with each model's stated cutoff and that model's own rate. Only tests whether the village COULD have been a source."""
import polars as pl
D='/Users/phosphorus/projects/prismql-data/ai-village/corpus/'
c=pl.scan_parquet(D+'chat_raw.parquet').filter(pl.col('kind')=='agent').select('time','agent','text').collect()
m=pl.read_csv(D+'analysis/models-table/models.csv').select('agent_name','knowledge_cutoff','cutoff_precision','village_joined')
P={'live and verified':r'(?i)live and verified','absolutely right':r"(?i)you'?re absolutely right|absolutely right",'exactly right':r'(?i)\bexactly right\b'}
for name,rx in P.items():
    h=c.filter(pl.col('text').str.contains(rx))
    first=h['time'].min()
    per=h.group_by('agent').agg(pl.len().alias('n'),pl.col('time').min().alias('own_first'))
    tot=c.group_by('agent').agg(pl.len().alias('tot'))
    t=m.join(tot,left_on='agent_name',right_on='agent',how='left').join(per,left_on='agent_name',right_on='agent',how='left').with_columns(
        (pl.col('n').fill_null(0)*1000/pl.col('tot')).round(1).alias('per1k'),
        pl.when(pl.col('knowledge_cutoff')=='unknown').then(None).otherwise(pl.col('knowledge_cutoff').str.slice(0,7) > str(first)[:7]).alias('cutoff_after_first_village_use'))
    print(f'\n### {name!r}: first village use {first} ({h.height} msgs)')
    print(t.filter(pl.col('agent_name').is_in(['GPT-5.6 Terra','GPT-5.6 Luna']).not_()).sort('per1k',descending=True).select('agent_name','knowledge_cutoff','per1k','own_first','cutoff_after_first_village_use').filter(pl.col('per1k')>0))
    print('first speaker:', h.sort('time')['agent'][0])
