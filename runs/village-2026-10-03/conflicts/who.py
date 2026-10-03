# Per-agent concession and directed-contradiction rates in chat; within- vs cross-lab.
import re, polars as pl
from agents import ALIASES, KEYS, LAB, COH, PROTECTED
C=pl.read_parquet('/Users/phosphorus/projects/prismql-data/ai-village/corpus/chat_raw.parquet',columns=['id','time','kind','agent','text']).filter(pl.col('kind')=='agent')
AT=re.compile(r'@(' + '|'.join(re.escape(k) for k in KEYS) + r')(?![\w]|[.\-]\d)')
CONC=r"(?i)\b(you['’]re (absolutely |totally |completely )?right|you are right|good catch|great catch|nice catch|my mistake|my error|I stand corrected|I was wrong|thanks for catching|thank you for catching|thanks for the correction|thank you for the correction|you['’]re correct)\b"
CONTRA=r"(?i)(doesn['’]t exist|does not exist|is incorrect|isn['’]t correct|is not correct|that['’]s wrong|that['’]s not (right|correct|accurate)|\bI (respectfully )?disagree|false positive|can['’]t reproduce|cannot reproduce|doesn['’]t match|does not match|not accurate|inaccurate|fabricated|hallucinated|\bcorrection:)"
C=C.with_columns(pl.col('text').str.contains(CONC).alias('concede'),pl.col('text').str.contains(CONTRA).alias('contra'))
# directed mentions
tg=[]
for a,t in zip(C['agent'],C['text']):
    s={ALIASES[m] for m in AT.findall(t or '')}; s.discard(a); tg.append(sorted(s))
C=C.with_columns(pl.Series('at',tg))
C=C.with_columns((pl.col('contra') & (pl.col('at').list.len()>0)).alias('dcontra'))
C.select('id','time','agent','concede','contra','dcontra','at').write_parquet('chat_flags.parquet')
per=C.group_by('agent').agg(pl.len().alias('msgs'),(pl.col('concede').sum()*1000/pl.len()).round(2).alias('concede_per1k'),
    (pl.col('dcontra').sum()*1000/pl.len()).round(2).alias('dcontra_per1k'),(pl.col('at').list.len()>0).mean().round(3).alias('at_share'))
per=per.filter(pl.col('msgs')>=500).with_columns(pl.col('agent').replace_strict(LAB).alias('lab'),pl.col('agent').replace_strict(COH).alias('cohort'))
per=per.with_columns(pl.when(pl.col('agent').is_in(list(PROTECTED))).then(pl.lit('[OpenAI 2026H2 member]')).otherwise(pl.col('agent')).alias('agent'))
pl.Config.set_tbl_rows(60)
print(per.sort('dcontra_per1k',descending=True))
print(per.group_by('lab').agg(pl.col('msgs').sum(), pl.col('concede_per1k').median(), pl.col('dcontra_per1k').median()))
# within vs cross lab: directed contradictions vs all directed mentions
E=C.filter(pl.col('at').list.len()>0).explode('at').with_columns(pl.col('agent').replace_strict(LAB).alias('la'),pl.col('at').replace_strict(LAB,default=None).alias('lb'))
E=E.with_columns((pl.col('la')==pl.col('lb')).alias('same_lab'))
print(E.group_by('same_lab').agg(pl.len().alias('mentions'),pl.col('dcontra').sum(),pl.col('dcontra').mean().round(4).alias('rate'),pl.col('concede').mean().round(4).alias('concede_rate')))
E.select('id','time','agent','at','la','lb','same_lab','dcontra','concede').write_parquet('directed_edges.parquet')
