"""C12 (report §11): accusation → retraction counts per window on the server (labels c12-*), with the twin
(accusation → any message) and the base rate. Writes g_<query>_<window>.json group files to the cwd (gitignored
results); labels.py holds the hand labels as indices into those files. usage: cd results/c12 && uv run python ../../runs/c12_accusations/run1.py"""
import json
from q import ev, page
P={'before':('2026-02-05T00:00:00Z','2026-03-05T00:00:00Z'),'game':('2026-03-05T00:00:00Z','2026-03-14T00:00:00Z'),'after':('2026-03-14T00:00:00Z','2026-04-11T00:00:00Z')}
ACC="field(kind, AGENT_TALK) AND field(agent, $a) AND contains(accuse) AND contains(artifact)"
Q={
 'acc': f"SELECT {ACC}",
 'acc_ret': f"SELECT {ACC} FOLLOWED_BY field(kind, AGENT_TALK) AND field(agent, $a) AND contains(retract) DURING 1 hour",
 'acc_any': f"SELECT {ACC} FOLLOWED_BY field(kind, AGENT_TALK) AND field(agent, $a) DURING 1 hour",
 'talk_ret': "SELECT field(kind, AGENT_TALK) AND field(agent, $a) FOLLOWED_BY field(kind, AGENT_TALK) AND field(agent, $a) AND contains(retract) DURING 1 hour",
 'talk_any': "SELECT field(kind, AGENT_TALK) AND field(agent, $a) FOLLOWED_BY field(kind, AGENT_TALK) AND field(agent, $a) DURING 1 hour",
 'talk': "SELECT field(kind, AGENT_TALK)",
}
res={}
for p,(a,b) in P.items():
    for k,q in Q.items():
        qq=f"{q} BETWEEN('{a}','{b}')"
        r=ev(qq+" AGGREGATE count()", f"c12-{k}-{p}")
        res[(p,k)]=r.get('value'); 
        if r.get('warnings'): print('WARN',p,k,r['warnings'])
        if not r.get('ok'): print('ERR',p,k,r)
        if k in ('acc','acc_ret','acc_any'):
            g=ev(qq, f"c12-{k}-{p}-groups", max_results=500)
            items=page(g['result_id'], g['total'])
            json.dump(items, open(f'g_{k}_{p}.json','w'))
            assert g['total']==len(items), (g['total'],len(items))
        print(p,k,res[(p,k)],flush=True)
