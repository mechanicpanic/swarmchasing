"""Triangles: messages that @B and name C without @-ing C = A talks to B about C. Plus monthly communities on reciprocal @-edges."""
import polars as pl, networkx as nx
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_width_chars(250)
E=pl.read_parquet('edges.parquet')
at=E.filter('is_at').select('id','src',pl.col('dst').alias('B'),'time')
ab=E.filter(~pl.col('is_at')).select('id',pl.col('dst').alias('C'))
T=at.join(ab,on='id').filter(pl.col('B')!=pl.col('C'))
print('A@B-about-C msgs', T['id'].n_unique())
about=T.group_by('C').agg(pl.col('id').n_unique().alias('n'),pl.struct('src','B').n_unique().alias('dyads')).sort('n',descending=True)
print(about.head(15))
# which C is discussed in a given A-B dyad most, relative to C's general mentions
tri=T.group_by('src','B','C').agg(pl.len().alias('n'),pl.col('time').min().alias('first'),pl.col('time').max().alias('last')).sort('n',descending=True)
print(tri.head(30))
tri.write_parquet('triangles.parquet')
# monthly communities
A=E.filter('is_at').with_columns(pl.col('time').dt.truncate('1mo').alias('mo')).group_by('mo','src','dst').agg(pl.len().alias('n'))
A2=A.join(A.rename({'src':'dst','dst':'src','n':'n2'}),on=['mo','src','dst']).filter(pl.col('src')<pl.col('dst')).with_columns(pl.min_horizontal('n','n2').alias('w')).filter(pl.col('w')>=5)
out=[]
for mo in sorted(A2['mo'].unique()):
    g=nx.Graph(); 
    for s,d,w in A2.filter(pl.col('mo')==mo).select('src','dst','w').iter_rows(): g.add_edge(s,d,weight=w)
    if g.number_of_nodes()<4: continue
    cs=nx.community.louvain_communities(g,weight='weight',seed=1)
    out.append(dict(mo=str(mo)[:7],q=round(nx.community.modularity(g,cs,weight='weight'),3),comms=[sorted(c) for c in sorted(cs,key=len,reverse=True)]))
for o in out: print(o['mo'],o['q'],' | '.join(', '.join(c) for c in o['comms']))
import json; json.dump(out,open('communities_monthly.json','w'),indent=1)
