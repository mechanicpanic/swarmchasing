import polars as pl
from agents import names_in
T=pl.read_parquet('thoughts.parquet').unique(['thought','event'])
CUES = {
 'distrust': r"(?i)\b(don.t|do not|can.t|cannot|not) (fully )?trust|skeptic|suspicious|unreliable|hallucinat|fabricat|false (claim|completion|report|positive)|never actually|didn.t actually|not actually (done|there|exist|merged|pushed|published|sent)|claim(s|ed)? (to have|that)[^.]{0,60}but|unverified|can.t verify|couldn.t verify|doesn.t (actually )?exist",
 'frustration': r"(?i)frustrat|annoy|irritat|exasperat|keeps? (saying|claiming|asking|repeating|posting|pinging|insisting|making)|yet again|over and over|ridiculous|tiresome|spamm|flood(ing)? the chat|noisy|cluttering",
 'turf': r"(?i)duplicat|redundant|overwr|stepp(ed|ing) on|took over my|my (work|task|pr|branch|file)|same (work|task) as|already (did|done|claimed|assigned|working on)|competing",
 'wrong': r"(?i)\b(is|was|are|were) (wrong|incorrect|mistaken|inaccurate)|incorrect(ly)?|mistaken|contradict|misreport|misleading|got it wrong|error in (their|his|her)",
 'ignored': r"(?i)ignor(ed|ing|es)|didn.t (respond|reply|answer)|hasn.t (responded|replied|answered)|no (response|reply) from|not responding|unresponsive|still waiting (on|for)",
}
cue_any='|'.join(f'(?:{v.replace("(?i)","")})' for v in CUES.values())
F=T.filter(pl.col('thought').str.contains('(?i)'+cue_any))
print('thoughts',T.height,'with any cue',F.height)
F=F.with_columns(pl.col('thought').str.extract_all(r'(?:[^.!?\n]|[.!?][^\s.!?])+[.!?]*').alias('sent')).explode('sent')
F=F.filter(pl.col('sent').str.contains('(?i)'+cue_any))
for k,v in CUES.items(): F=F.with_columns(pl.col('sent').str.contains(v).alias(k))
rows=[]
for r in F.select('time','agent','of','event','sent','event_kind','event_text',*CUES).iter_rows(named=True):
    tg=[n for n in names_in(r['sent']) if n!=r['agent']]
    if tg:
        r['targets']=tg; rows.append(r)
S=pl.DataFrame(rows).with_columns(pl.col('event_text').str.slice(0,2000))
S.write_parquet('thought_friction_sents.parquet')
print('sentences with cue + other agent',S.height)
print(S.select(list(CUES)).sum())
