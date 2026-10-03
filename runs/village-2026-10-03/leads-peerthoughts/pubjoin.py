import polars as pl
P=pl.read_parquet('peer_sents_all_scores.parquet')
E=(pl.scan_parquet('../conflicts/thoughts.parquet').filter(pl.col('of')=='AGENT_TALK').select('agent','event','event_text')
   .unique(['agent','event']).collect())
P=P.join(E,on=['agent','event'],how='left')
print(P.select(pl.col('event_text').is_not_null().sum(), pl.len()))
P.write_parquet('peer_sents_all_scores.parquet')
