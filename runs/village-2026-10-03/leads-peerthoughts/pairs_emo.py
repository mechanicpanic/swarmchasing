import polars as pl
pl.Config.set_tbl_rows(40); pl.Config.set_tbl_width_chars(200); pl.Config.set_fmt_str_lengths(40)
P=pl.read_parquet('peer_sents_all_scores.parquet').filter(pl.col('nw')>=6).explode('subjects').rename({'subjects':'subject'})
P=P.with_columns((pl.col('e_anger')+pl.col('e_disgust')).alias('neg'))
base=P.select(pl.col('neg').mean(),pl.col('e_joy').mean(),(pl.col('neg')>0.5).mean().alias('negrate')); print(base)
# by thinker
print(P.group_by('agent').agg(pl.len(),(pl.col('neg')>0.5).mean().round(4).alias('negrate'),(pl.col('e_joy')>0.5).mean().round(3).alias('joyrate')).filter(pl.col('len')>500).sort('negrate',descending=True))
# by subject
print(P.group_by('subject').agg(pl.len(),(pl.col('neg')>0.5).mean().round(4).alias('negrate'),(pl.col('e_joy')>0.5).mean().round(3).alias('joyrate'),(pl.col('e_sadness')>0.5).mean().round(3).alias('sadrate')).filter(pl.col('len')>500).sort('negrate',descending=True))
pairs=P.group_by('agent','subject').agg(pl.len(),(pl.col('neg')>0.5).sum().alias('nneg'),(pl.col('e_joy')>0.5).sum().alias('njoy')).filter(pl.col('len')>=300)
pairs=pairs.with_columns((pl.col('nneg')/pl.col('len')).round(4).alias('negrate'),(pl.col('njoy')/pl.col('len')).round(3).alias('joyrate'))
print(pairs.sort('negrate',descending=True).head(20)); print(pairs.sort('joyrate',descending=True).head(15))
pairs.write_parquet('pairs_emotion.parquet')
