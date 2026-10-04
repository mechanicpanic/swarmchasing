"""C5: fairness tests on the roll table (chi-square vs uniform, binomial on 1s), private vs public claims, by family and day."""
import os
import polars as pl
from scipy import stats
df=pl.read_csv(os.environ.get('OUT', '../../results/c5_rolls_by_agent_day.csv'))
def test(vals,label):
    n=len(vals); c=[vals.count(f) for f in range(1,7)]
    if n==0: print(label,'n=0'); return
    chi=stats.chisquare(c); k=c[0]
    lo=stats.binomtest(k,n,1/6,alternative='less').pvalue
    hi=stats.binomtest(k,n,1/6,alternative='greater').pvalue
    print(f"{label:48s} n={n:2d} faces1-6={c} chi2={chi.statistic:.2f} p={chi.pvalue:.3f} | ones={k} exp={n/6:.1f} P(<=k)={lo:.3f} P(>=k)={hi:.3f}")
print(df.group_by('evidence').len().sort('evidence'))
p=df.filter(pl.col('priv_value').is_not_null())
test(p['priv_value'].to_list(),'private, all with a value')
test(p.filter(pl.col('evidence')!='pretend')['priv_value'].to_list(),'private, excl. pretend')
test(p.filter(pl.col('evidence').is_in(['cmd','session']))['priv_value'].to_list(),'private, cmd or roll-session')
test(p.filter(pl.col('evidence')=='cmd')['priv_value'].to_list(),'private, named command only')
test(p.filter(pl.col('evidence')=='asserted')['priv_value'].to_list(),'private, asserted only')
test(p.filter(pl.col('evidence')=='pretend')['priv_value'].to_list(),'private, pretend only')
q=df.filter(pl.col('pub_value').is_not_null())
test(q['pub_value'].to_list(),'public first claim, all')
# public claims on days w/ private
both=df.filter(pl.col('priv_value').is_not_null()&pl.col('pub_value').is_not_null())
print('both private and public:',both.height,' agree:',both.filter(pl.col('priv_value')==pl.col('pub_value')).height)
print(both.filter(pl.col('priv_value')!=pl.col('pub_value')).select('day','agent','priv_value','pub_value','evidence','pub_role'))
ones=df.filter(pl.col('priv_value')==1)
print(ones.select('day','agent','evidence','pub_value','pub_role'))
# by family
fam=lambda a: 'Claude' if ('Claude' in a or 'Opus' in a) else ('GPT' if 'GPT' in a else ('Gemini' if 'Gemini' in a else 'DeepSeek'))
p2=p.with_columns(pl.col('agent').map_elements(fam,return_dtype=pl.String).alias('fam'))
for f in ['Claude','GPT','Gemini','DeepSeek']:
    test(p2.filter((pl.col('fam')==f)&(pl.col('evidence')!='pretend'))['priv_value'].to_list(),f'  family {f}, excl pretend')
for d in sorted(set(df['day'])):
    test(p.filter((pl.col('day')==d)&(pl.col('evidence')!='pretend'))['priv_value'].to_list(),f'  day {d}')
# what the public (pub-only) record would show: union per agent-day of public claim
print('agent-days with no private value but a public claim:', df.filter(pl.col('priv_value').is_null()&pl.col('pub_value').is_not_null()).height)
print('agent-days with neither:', df.filter(pl.col('priv_value').is_null()&pl.col('pub_value').is_null()).select('day','agent','notes'))
