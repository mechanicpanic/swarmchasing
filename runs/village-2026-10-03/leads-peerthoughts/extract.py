# Extract sentences in THOUGHT rows that name another agent (all of them), plus human/organiser sentences.
import sys, re, polars as pl
sys.path.insert(0,'../conflicts')
from agents import ALIASES, names_in
T=(pl.scan_parquet('../conflicts/thoughts.parquet').select('time','agent','of','event','thought','event_kind')
   .sort('time').unique(['agent','thought'],keep='first').collect())
print('deduped thoughts',T.height)
SPLIT=r'(?:[^.!?\n]|[.!?][^\s.!?])+[.!?]*'   # conflicts splitter: keeps GPT-5.1 intact
S=(T.with_row_index('tid').with_columns(pl.col('thought').str.extract_all(SPLIT).alias('sent')).drop('thought')
   .explode('sent').with_columns(pl.col('sent').str.strip_chars()).filter(pl.col('sent').str.len_chars()>=15))
S=S.with_columns(pl.int_range(pl.len()).over('tid').alias('sidx'))
print('sentences',S.height)
pat='(?i)'+'|'.join(re.escape(k) for k in sorted(ALIASES,key=len,reverse=True))
C=S.filter(pl.col('sent').str.contains(pat))
rows=[]
for r in C.iter_rows(named=True):
    tg=[n for n in names_in(r['sent']) if n!=r['agent']]
    if tg:
        r['subjects']=tg; rows.append(r)
P=pl.DataFrame(rows).with_columns(pl.col('sent').str.slice(0,600))
P.write_parquet('peer_sents_raw.parquet')
print('peer sentences',P.height, 'unique text',P['sent'].n_unique())
HUM=r"(?i)\b(the (user|human|humans|organi[sz]ers?|admins?|visitors?|viewers?|readers?|audience|operator|team behind)|humans?\b|organi[sz]ers?|village (staff|team|admins?)|help desk)"
H=S.filter(pl.col('sent').str.contains(HUM)).with_columns(pl.col('sent').str.slice(0,600))
H.write_parquet('human_sents_raw.parquet'); print('human sentences',H.height)
