import json, sys, re, polars as pl
fn=sys.argv[1]; n=int(sys.argv[2]); src=sys.argv[3] if len(sys.argv)>3 else 'chat'
if src=='full':
    T=pl.read_parquet('thoughts.parquet',columns=['event','thought','event_text'])
    th={e+':thought':t for e,t,_ in T.rows()}; ev={e:x for e,_,x in T.rows()}
    get=lambda i: th.get(i) or ev.get(i) or ''
else:
    C=pl.read_parquet('/Users/phosphorus/projects/prismql-data/ai-village/corpus/chat_raw.parquet',columns=['id','agent','text'])
    m={i:(a,t) for i,a,t in C.rows()}; get=lambda i: '%s: %s'%m.get(i,('?',''))
pat=re.compile(sys.argv[4],re.I) if len(sys.argv)>4 else None
for k,l in enumerate(open(fn)):
    if k>=n: break
    g=json.loads(l); print('##',g['times'][0][:16],g.get('bindings'))
    for i in g['ids']:
        t=get(i)
        if pat and ':thought' in i:
            s=[z for z in re.split(r'(?<=[.!?])\s+',t) if pat.search(z)]; t=' / '.join(s)
        print('   ',('T ' if ':thought' in i else 'S '),t[:280].replace('\n',' '))
