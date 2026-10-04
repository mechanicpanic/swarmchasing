"""Adds room co-presence to pair_weekly: room_copresent = both agents posted >=3 (deduped) msgs in the same room that week; shared_room = that room."""
import polars as pl
M=pl.read_parquet('msgs.parquet').filter(~pl.col('dup'))
ar=M.group_by('agent','week','room').agg(pl.len().alias('n')).filter(pl.col('n')>=3)
W=pl.read_parquet('pair_weekly.parquet').drop([c for c in ['room_copresent','shared_room'] if c in pl.read_parquet_schema('pair_weekly.parquet')])
j=W.select('src','dst','week').join(ar.rename({'agent':'src','n':'na'}),on=['src','week']).join(ar.rename({'agent':'dst','n':'nb'}),on=['dst','week','room'])
j=j.sort(pl.min_horizontal('na','nb'),descending=True).unique(['src','dst','week'],keep='first').select('src','dst','week',pl.col('room').alias('shared_room'))
W=W.join(j,on=['src','dst','week'],how='left').with_columns(pl.col('shared_room').is_not_null().alias('room_copresent'))
W.write_parquet('pair_weekly.parquet'); print(W.group_by('copresent','room_copresent').len())
