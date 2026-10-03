# Merge every generator's leads.jsonl into one ranked table + LEADS_ranked.csv.
import json, glob, re
from collections import Counter
rows=[]
for f in sorted(glob.glob("leads-*/leads.jsonl")):
    for i,l in enumerate(open(f)):
        l=l.strip()
        if not l: continue
        try: d=json.loads(l)
        except Exception: continue
        d["_gen"]=f.split("/")[0].replace("leads-",""); d["_order"]=i
        rows.append(d)
def agents(d):
    a=d.get("agents") or []
    return {x for x in (a if isinstance(a,list) else [a]) if isinstance(x,str)}
def months(d):
    return set(re.findall(r"20\d\d-\d\d", str(d.get("when",""))))
# convergence: other generators' leads sharing >=1 agent and >=1 month
for d in rows:
    A,M=agents(d),months(d)
    d["_conv"]=len({e["_gen"] for e in rows if e["_gen"]!=d["_gen"] and A&agents(e) and M&months(e)})
conf={"high":3,"medium":2,"low":1}
for d in rows:
    n=sum(1 for e in rows if e["_gen"]==d["_gen"])
    d["_score"]=conf.get(str(d.get("confidence","")).lower(),1)*2 + (2 if d.get("read") else 0) + min(d["_conv"],3) + 2*(1-d["_order"]/max(n,1))
rows.sort(key=lambda d:-d["_score"])
import csv
with open("LEADS_ranked.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["rank","score","generator","id","type","confidence","read","converges_with_generators","when","agents","hook","next_step"])
    for r,d in enumerate(rows,1):
        w.writerow([r,round(d["_score"],1),d["_gen"],d.get("id"),d.get("type"),d.get("confidence"),d.get("read"),d["_conv"],d.get("when"),"; ".join(sorted(agents(d))),d.get("hook"),d.get("next_step")])
print(len(rows),"leads"); print(Counter(d["_gen"] for d in rows)); print(Counter(str(d.get("type")) for d in rows).most_common(10))
for d in rows[:45]:
    print(f'{round(d["_score"],1):>5} {d["_gen"][:13]:<13} c{d["_conv"]} {str(d.get("when"))[:22]:<22} {str(d.get("hook"))[:120]}')
