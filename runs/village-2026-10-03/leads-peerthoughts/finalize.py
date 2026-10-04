import polars as pl
from nliload import KEYS
LAB=["engagement/status roster","publications & articles","files/JSON tech work","counts & leaderboards","interesting news from peer","bug reports","village announcements","email checking","fixing issues / stuck","milestones","awaiting peer's URL","respond to chat message","generic 'X is working on it'","timing & schedules","Substack","monitor & follow-up plans","PR review","monitoring duty","roster lists","collaboration & research","computer sessions","outreach replies / no response","validation & verification work","memory consolidation events","challenge scores","day planning","findings & analysis coordination","museum exhibits","pauses","radio silence / quiet","ethics & governance","directed messages","repo fixes","respond-to plans","readiness confirmations","analytics","merging PRs","DeepSeek-named items","waiting","bold-name headers","Echoes chapters","peer updates","file/archive availability","checking for updates","data transfer in chunks","using computer","division of labour","acknowledge message","GitHub work","pings","chapter writing","who replied to whom","grading","o3 hot-fixes","verification consensus","links/URLs","hub updates","PR reviewing","PR scores & issues","verifying","tracker","CSV export waiting","documentation","session timestamps","DeepSeek exhibit","automated nudges","chapters","Twitter","Cosmos chapters","stopped computer","multiple agents on computers","posted-at timestamps","advice to peer","monitoring checks","GO/NO-GO gates","votes","short-name references","plans & proposals","check chat for messages","started computer session"]
assert len(LAB)==80
C=pl.read_parquet('peer_sents_clustered.parquet',columns=['cluster']).with_row_index('rid')
P=pl.read_parquet('peer_sents_all_scores.parquet').join(C,on='rid')
N=pl.read_parquet('nli_pool.parquet')
P=P.join(N,on='rid',how='left')
nl=['n_'+k for k in KEYS]
P=P.with_columns(pl.concat_list(nl).alias('_v'))
P=P.with_columns(pl.col('_v').list.arg_max().alias('_i'),pl.col('_v').list.max().alias('stance_score'))
P=P.with_columns(pl.when(pl.col('stance_score')>=0.85).then(pl.col('_i').map_elements(lambda i: KEYS[i],return_dtype=pl.Utf8)).otherwise(None).alias('stance_nli'))
emo=['anger','disgust','fear','joy','neutral','sadness','surprise']
P=P.with_columns(pl.concat_list(['e_'+e for e in emo]).list.arg_max().map_elements(lambda i: emo[i],return_dtype=pl.Utf8).alias('emotion'))
P=P.with_columns(pl.col('cluster').map_elements(lambda c: LAB[c],return_dtype=pl.Utf8).alias('cluster_label'))
out=P.explode('subjects').select(pl.col('sent').alias('sentence'),pl.col('agent').alias('thinker'),pl.col('subjects').alias('subject'),
   'cluster','cluster_label','stance_nli','stance_score','emotion',*['e_'+e for e in emo],*nl,'time','of','event',pl.col('event_text').alias('next_public_msg'))
out.write_parquet('peer_thought_clusters.parquet')
print(out.height, out.columns)
print(out.group_by('stance_nli').len().sort('len',descending=True))
