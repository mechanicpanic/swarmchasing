# Tight interpersonal-friction sentences in THOUGHTS: target agent named, then a negative behaviour cue within 60 chars.
import re, polars as pl
from agents import ALIASES, names_in
S=pl.read_parquet('thought_friction_sents.parquet')
inv={}
for k,v in ALIASES.items(): inv.setdefault(v,[]).append(k)
CUE=r"(keeps? (saying|claiming|repeating|posting|asking|insisting|making|pinging|sending)|kept (saying|claiming|repeating|posting|asking|failing)|(hasn.t|hadn.t|never|didn.t|doesn.t) actually|dropped the ball|(is|was|were|are) (wrong|mistaken|incorrect)|got (it|this) wrong|ignor(ed|ing)|duplicat(ed|ing)|overwr(o|i)te|stepp(ed|ing) on|false (positive|claim|completion)|fabricat|hallucinat|suspicious|unreliable|doubling down|seems stuck in a loop|stuck in a loop|not trust|isn.t listening|talking past)"
def tight(sent, targets):
    hits=[]
    for t in targets:
        for al in inv.get(t,[t]):
            if re.search(re.escape(al)+r"(?:'s)?\b[^.;]{0,60}?"+CUE, sent, re.I):
                hits.append(t); break
    return hits
rows=[]
for r in S.iter_rows(named=True):
    h=tight(r['sent'], r['targets'])
    if h:
        pub=r['event_text'] if r['event_kind']=='AGENT_TALK' else None
        rows.append(dict(time=r['time'],agent=r['agent'],target=h[0],sent=r['sent'].strip(),event_kind=r['event_kind'],public=pub,
                         public_names_target=bool(pub and h[0] in names_in(pub))))
G=pl.DataFrame(rows).unique(['agent','sent'])
G=G.with_columns(((pl.col('time')>='2026-03-05')&(pl.col('time')<'2026-03-17')).alias('saboteur_game'))
G.write_parquet('gap_tight.parquet')
print(G.height, G.group_by('saboteur_game').len())
