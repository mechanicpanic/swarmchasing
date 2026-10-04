import json, sys, os
# reads a JSON list from stdin; assigns ids sequentially; appends to leads.jsonl
F='leads.jsonl'
n=sum(1 for _ in open(F)) if os.path.exists(F) else 0
L=json.load(sys.stdin)
with open(F,'a') as f:
    for d in L:
        n+=1
        d={'id':f'peerthoughts-{n}','generator':'peer-thoughts',**d}
        for k in ['Terra','Luna']: assert k not in json.dumps(d), 'privacy'
        f.write(json.dumps(d,ensure_ascii=False)+'\n')
print('total',n)
