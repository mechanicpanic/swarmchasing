import polars as pl, sys
pat=sys.argv[1]; n=int(sys.argv[2]) if len(sys.argv)>2 else 40
c=pl.read_parquet('/Users/phosphorus/projects/prismql-data/ai-village/corpus/chat_raw.parquet',columns=['time','kind','agent','room','text'])
s=c.filter(pl.col('text').str.contains(pat)).sort('time')
print(s.height)
for t,k,ag,rm,tx in s.head(n).rows():
    print(str(t)[:16],rm,k,ag,'|',tx[:350].replace('\n',' '))
