import sys,re,polars as pl
d=pl.read_ndjson('/Users/phosphorus/projects/prismql-data/ai-village/summaries.jsonl.gz')
rx=sys.argv[1]; flt=sys.argv[2] if len(sys.argv)>2 else ''
for r in d.iter_rows(named=True):
    key=f"{r['type']}|{r['summary_target']}|{r['summary_date']}"
    if flt and not re.search(flt,key): continue
    for m in re.finditer(rx,r['content'],re.I|re.S):
        s=max(0,m.start()-250); e=min(len(r['content']),m.end()+250)
        print(f"== {r['id']} {key} {r['generated_by']} {r['created_at'][:10]}\n...{r['content'][s:e]}...\n")
