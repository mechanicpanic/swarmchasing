import json,sys
p='/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/leads-summaries/parts/leads_M.jsonl'
keys=["id","generator","type","hook","agents","when","evidence","example","read","confidence","why_it_matters","next_step"]
d=json.loads(sys.stdin.read())
for k in keys: assert k in d,k
open(p,'a').write(json.dumps(d,ensure_ascii=False)+'\n'); print('ok',d['id'])
