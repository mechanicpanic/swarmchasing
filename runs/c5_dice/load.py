"""C5 (report §5): the March 2026 egg-saboteur game window. VILLAGE = path to data/village.parquet."""
import os
import polars as pl
from datetime import datetime, timezone
d=pl.read_parquet(os.environ.get('VILLAGE', '../../data/village.parquet'), columns=['id','time','kind','agent','room','text','event','of','cu_session'])
w=d.filter((pl.col('time')>=datetime(2026,3,4,tzinfo=timezone.utc))&(pl.col('time')<datetime(2026,3,19,tzinfo=timezone.utc)))
