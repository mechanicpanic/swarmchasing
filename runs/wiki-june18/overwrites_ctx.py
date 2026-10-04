import pickle,re
revs=pickle.load(open('dse_revs.pkl','rb'))
N=lambda x: re.sub(r'[^A-Za-z0-9]','',x)
cases=[('TestSeite','2026-06-16T19:31'),('CashierCoordApr02OAI','2026-06-17T04:36'),('CashierCoordNov21OAI','2026-06-17T05:31'),('CashierCoordJul18OAI','2026-06-17T09:15'),('OpenAIConstructionSep20Live','2026-06-17T16:13'),('NYCVeteransSequenceCollabJul03','2026-06-17T16:28'),('DataUSAPovertyDec09Cohort2028','2026-06-19T21:38'),('DataUSAConstructionWageJun26Live','2026-06-19T23:03'),('ZZZEnrollmentAsianFeb21Help','2026-06-19T23:43'),('OECDEducationEquitySequence','2026-06-20T00:21'),('OECDEquityLiveJul10','2026-06-20T01:01'),('OpenAICVDDec08Fast2028','2026-06-21T02:08'),('OECDRegionalRecoveryCO2Sequence','2026-06-21T19:59'),('DataUSALanguageLiveRound4','2026-06-16T23:23'),('AgentTempLAProd2013','2026-06-19T05:20'),('StartSeite','2026-05-27T07:11')]
for page,t in cases:
    rs=sorted(revs[page],key=lambda r:r['seq'])
    i=[k for k,r in enumerate(rs) if r['time'].startswith(t)][-1]
    print('=====',page,t)
    for r in rs[max(0,i-4):i+2]:
        print('  ',r['seq'],r['time'][5:19],(r['label'] or '')[:28],r['ip16'],'len',len(r['body']),'|',(r['change_summary'] or '')[:60])
    # what restorer added that's new text
    prev=rs[i-1]['body']; nb=N(prev)
    new=[l for l in rs[i]['body'].split('\n') if l.strip() and N(l) not in nb]
    print('   NEW:', ' / '.join(new)[:500])
