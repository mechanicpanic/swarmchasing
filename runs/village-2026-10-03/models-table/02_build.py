"""Build models.csv from agents_times.parquet (01_agents.py) + research_*.jsonl (web-sourced by subagents, spot-checked)."""
import json, glob, polars as pl
D='/Users/phosphorus/projects/prismql-data/ai-village/corpus/analysis/models-table/'
res={}
for f in sorted(glob.glob(D+'research_*.jsonl')):
    for l in open(f):
        r=json.loads(l); res[r['model_string']]=r

# Editorial overrides (see REPORT.md "Method"):
# - lab-stated values only in knowledge_cutoff; third-party values demoted to notes.
THIRD_PARTY={'kimi-k2.6':'third-party only (Kili: "around April 2025"), not a lab statement',
             'z-ai/glm-5.2':'third-party only (Handy AI newsletter: "Knowledge cutoff March 2026"), not found on any Z.ai page'}
# - which kind of cutoff the knowledge_cutoff column holds
def kind(ms):
    if ms.startswith('claude'):
        return 'reliable' if ms in ('claude-3-5-sonnet-20241022','claude-opus-4-1-20250805') else 'training_data'
    if ms.startswith('gemini-3.1') or ms.startswith('gemini-3.5'): return 'inherited_from_base_model'
    return 'knowledge_cutoff (lab term)'
RELIABLE={'claude-3-5-sonnet-20241022':'2024-04','claude-3-7-sonnet-20250219':'2024-10','claude-opus-4-20250514':'2025-01',
 'claude-opus-4-1-20250805':'2025-01','claude-sonnet-4-5-20250929':'2025-01','claude-haiku-4-5-20251001':'2025-02',
 'claude-opus-4-5-20251101':'2025-05','claude-opus-4-6':'2025-05','claude-sonnet-4-6':'2025-08','claude-opus-4-7':'2026-01',
 'claude-opus-4-8':'2026-01','claude-fable-5':'2026-01','claude-sonnet-5':'2026-01','claude-opus-5':'2026-05','claude-fable-5-1':'2026-06'}

def half(d):
    if not d or d=='unknown': return 'unknown'
    y,m=int(d[:4]),int(d[5:7]); return f'{y}H{1 if m<=6 else 2}'

a=pl.read_parquet(D+'agents_times.parquet')
SKIP={'[Temporary] Fine-tuned Leader','Fine-Tuned Leader'}
rows=[]
for r in a.iter_rows(named=True):
    if r['name'] in SKIP: continue
    ms=r['model_string']; base=ms.replace('claude-code::','')
    x=res[base]
    kc=x['knowledge_cutoff']; prec=x['cutoff_precision']; csrc=x['cutoff_source']; notes=x['notes']
    if base in THIRD_PARTY:
        notes=f'CUTOFF: {THIRD_PARTY[base]}; set to unknown here. '+notes; kc='unknown'; prec='unknown'
    if kc=='unknown': csrc=csrc if csrc and csrc!='unknown' and base not in THIRD_PARTY else ''
    if ms.startswith('claude-code::'):
        notes='Same weights as Claude Opus 4.5, run inside the Claude Code harness (0 tokens metered by the village). '+notes
    lab={'Zhipu':'Zhipu (Z.ai)','Moonshot':'Moonshot AI'}.get(r['lab'],r['lab'])
    rows.append(dict(agent_name=r['name'],model_string=ms,lab=lab,family=r['family'],
        release_date=x['release_date'],release_source=x['release_source'],
        knowledge_cutoff=kc,cutoff_source=csrc,cutoff_precision=prec.split(' ')[0] if prec else 'unknown',
        cutoff_kind=kind(base) if kc!='unknown' else 'unknown',
        reliable_cutoff=RELIABLE.get(base,''),
        village_created=str(r['created_at'])[:19],
        village_joined=str(r['first_msg'])[:19],village_last_msg=str(r['last_msg'])[:19],n_msgs=r['n_msgs'],
        cutoff_half=half(kc),release_half=half(x['release_date']),
        notes=notes,no_behavioural_naming=r['name'] in ('GPT-5.6 Terra','GPT-5.6 Luna')))
df=pl.DataFrame(rows)
# staleness: months from cutoff (start of stated period) to first village message; release->join lag in days
def mdiff(c,j):
    if c=='unknown': return None
    return (int(j[:4])-int(c[:4]))*12+int(j[5:7])-int(c[5:7])
df=df.with_columns(
  pl.struct('knowledge_cutoff','village_joined').map_elements(lambda s: mdiff(s['knowledge_cutoff'],s['village_joined']),return_dtype=pl.Int64).alias('months_cutoff_to_join'),
  pl.struct('release_date','village_joined').map_elements(lambda s: None if s['release_date']=='unknown' else (pl.Series([s['village_joined'][:10]]).str.to_date()-pl.Series([s['release_date']]).str.to_date()).dt.total_days()[0],return_dtype=pl.Int64).alias('days_release_to_join'))
df.write_csv(D+'models.csv')
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_width_chars(250)
print(df.select('agent_name','release_date','knowledge_cutoff','cutoff_precision','cutoff_kind','reliable_cutoff','village_joined','months_cutoff_to_join','days_release_to_join'))

# reorder: requested columns first, extras after
req=['agent_name','model_string','lab','family','release_date','release_source','knowledge_cutoff','cutoff_source','cutoff_precision','village_joined','village_last_msg','notes','no_behavioural_naming','cutoff_half','release_half']
df=df.select(req+[c for c in df.columns if c not in req])
df.write_csv(D+'models.csv')
k=df.filter(pl.col('knowledge_cutoff')!='unknown').unique('model_string')
print('distinct models',df['model_string'].n_unique(),'with lab cutoff',k.height)
print(k.group_by('lab').agg(pl.col('months_cutoff_to_join').median().alias('med_months'),pl.col('months_cutoff_to_join').min().alias('min'),pl.col('months_cutoff_to_join').max().alias('max'),pl.len()).sort('lab'))
print('overall median months cutoff->join',k['months_cutoff_to_join'].median())
pub='2025-04'; print('cutoff >= village public (2025-04):',k.filter(pl.col('knowledge_cutoff').str.slice(0,7)>=pub).sort('knowledge_cutoff')[['agent_name','knowledge_cutoff']].rows())
print('reliable cutoff >= 2025-04 (Anthropic):',df.filter((pl.col('reliable_cutoff')!='')&(pl.col('reliable_cutoff')>=pub))['agent_name'].to_list())
print('cutoff >= HF dataset 2026-06:',k.filter(pl.col('knowledge_cutoff').str.slice(0,7)>='2026-06')['agent_name'].to_list())
print(df.group_by('cutoff_half').len().sort('cutoff_half'))
