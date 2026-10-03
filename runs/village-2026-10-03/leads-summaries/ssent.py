import sys,re,polars as pl
d=pl.read_ndjson('/Users/phosphorus/projects/prismql-data/ai-village/summaries.jsonl.gz')
flt,rx=sys.argv[1],sys.argv[2]
for r in d.iter_rows(named=True):
    key=f"{r['type']}|{r['summary_target']}|{r['summary_date']}"
    if not re.search(flt,key): continue
    sents=re.split(r'(?<=[.!?])\s+|\n',r['content'])
    hits=[s for s in sents if re.search(rx,s,re.I)]
    if hits:
        print(f"== {r['id']} {key} {r['generated_by']}")
        for h in hits: print('   >',h[:700])
