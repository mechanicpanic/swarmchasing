"""The 14 teaching queries of notes/2026-10-04-prismql-cheatsheet.md, ported to this repo's `village` corpus.
usage: PRISMQL_URL=… PRISMQL_CLIENT=… uv run python runs/village_cheatsheet.py [NN ...]   (no ids = all)

The cheatsheet ran on a teammate's corpora: `village_chat` (chat rows only, kind agent/user), `village`
(chat + memory), `village_full` (+ THOUGHT rows, emb). Here one corpus holds every AI Village event, so:
  kind agent -> AGENT_TALK, kind user -> USER_TALK, kind THOUGHT -> THOUGHT;
  kind memory -> STOP_USING_COMPUTER (the session summary an agent writes when it leaves its computer;
    this export has no memory-file rows, and CONSOLIDATE rows hold no text these phrases match);
  a leg that was implicitly chat (village_chat has nothing else) gets CHAT = AGENT_TALK or USER_TALK,
    else THOUGHT and computer-session rows answer too (01 stays one field, so it counts every kind).
THOUGHT and computer rows sit between chat rows here, so INWINDOW counts them (gotcha #158 in graph
@aleph/prismql): 12 widens INWINDOW 5 to 15 (chat is about a third of the rows; INWINDOW 5 gives 0).
09: the original word lists (contradict/pushback/retract) live in a dicts.json on the teammate's machine,
not in this repo -> not portable; the substitute uses the repo's own `accuse`/`retract` lists
(runs/c12_accusations/q.py) and an unconstrained middle reply.
13: similar_to needs the `emb` column -- needs embeddings (not in a judge's build)."""
import json, os, sys, urllib.request
URL = os.environ.get("PRISMQL_URL", "http://localhost:8931")
CLIENT = os.environ.get("PRISMQL_CLIENT", "claude-cheatsheet-port")
CORPUS = "village"
D09 = {  # verbatim from runs/c12_accusations/q.py (report §11)
    "accuse": ["doesn't exist", "does not exist", "don't exist", "do not exist", "doesn’t exist", "don’t exist", "didn't exist",
               "didn’t exist", "nonexistent", "non-existent", "phantom", "fabricated", "fabricating", "fabrication",
               "never existed", "isn't real", "is not real"],
    "retract": ["i was wrong", "i was incorrect", "was wrong", "was incorrect", "my mistake", "my error", "my bad", "apologize",
                "apologise", "apologies", "apology", "retract", "does exist", "do exist", "i stand corrected", "i was mistaken",
                "i misspoke"],
}
TALK = "field(kind, AGENT_TALK)"
CHAT = "(field(kind, AGENT_TALK) OR field(kind, USER_TALK))"
Q = [  # NN, name, construct, cheatsheet count, query (None = not portable), dictionaries
    ("01", "filter", "filter: one field", "5,481",
     'SELECT field(agent, "Claude Opus 4.8")', None),
    ("02", "and", "AND: two conditions on one event", "192",
     f'SELECT {TALK} AND contains_phrase("live and verified")', None),
    ("03", "sequence", "FOLLOWED_BY within a time window", "22",
     f'SELECT {CHAT} AND field(agent, "Gemini 3 Pro") AND contains_phrase("divergent reality") '
     f'FOLLOWED_BY contains_phrase("divergent reality") AND {TALK} DURING 1 hour', None),
    ("04", "same-var", "same variable in two legs ($a, $y)", "27,221",
     f'SELECT {TALK} AND field(agent, $a) AND mentions_user($y) '
     f'FOLLOWED_BY {CHAT} AND field(agent, $y) AND mentions_user($a) DURING 1 hour', None),
    ("05", "different-var", "different variable (!$a)", "273",
     f'SELECT {CHAT} AND contains_phrase("chaotic swarm") AND field(agent, $a) '
     f'FOLLOWED_BY {CHAT} AND contains_phrase("chaotic swarm") AND field(agent, !$a) DURING 1 day', None),
    ("06", "never-followed", "NOT_FOLLOWED_BY", "11,890",
     f'SELECT {TALK} AND field(agent, $a) AND mentions_user($y) '
     f'NOT_FOLLOWED_BY {CHAT} AND field(agent, $y) AND mentions_user($a) DURING 1 hour', None),
    ("07", "heard-before", "PRECEDED_BY", "177",
     f'SELECT {CHAT} AND contains_phrase("live and verified") AND field(agent, $b) '
     f'PRECEDED_BY {CHAT} AND contains_phrase("live and verified") AND field(agent, !$b) DURING 30 days', None),
    ("08", "first-use", "NOT_PRECEDED_BY (first use by me)", "26",
     f'SELECT {CHAT} AND contains_phrase("live and verified") AND field(agent, $b) '
     f'NOT_PRECEDED_BY {CHAT} AND contains_phrase("live and verified") AND field(agent, $b) DURING 400 days', None),
    ("09", "three-legs", "three legs (A, B, A) -- original not portable: contradict/pushback/retract word lists "
     "are in a dicts.json outside the repo; substitute uses the repo's c12 accuse/retract lists", "37",
     f'SELECT {TALK} AND field(agent, $a) AND mentions_user($b) AND contains(accuse) '
     f'FOLLOWED_BY {CHAT} AND field(agent, $b) '
     f'FOLLOWED_BY {CHAT} AND field(agent, $a) AND contains(retract) DURING 1 hour', D09),
    ("10", "chat-summary-chat", "across kinds: chat -> session summary (stands in for memory) -> chat", "321",
     f'SELECT contains_phrase("chaotic swarm") AND {TALK} AND field(agent, $a) '
     'FOLLOWED_BY contains_phrase("chaotic swarm") AND field(kind, STOP_USING_COMPUTER) AND field(agent, $b) AND field(agent, !$a) '
     f'FOLLOWED_BY contains_phrase("chaotic swarm") AND {TALK} AND field(agent, $b) DURING 30 days', None),
    ("11", "run", "RUN: an unbroken streak", "203",
     f'SELECT RUN({CHAT} AND field(agent, $a) AND contains_phrase("standing by")){{5,}} DURING 30 minutes', None),
    ("12", "unordered", "unordered INWINDOW (comma list); window 5 -> 15, see top", "4",
     f'SELECT {CHAT} AND contains_phrase("export control"), field(kind, USER_TALK) INWINDOW 15', None),
    ("13", "meaning", "similar_to -- needs embeddings (not in a judge's build)", "291",
     'SELECT field(kind, THOUGHT) AND similar_to("I am blocked and should ask a human helper", 0.5)', None),
    ("14", "count", "GROUP BY ... AGGREGATE count()", "Claude 3.7 Sonnet 35, Gemini 2.5 Pro ...",
     f'SELECT {CHAT} AND contains_phrase("absolutely right") GROUP BY agent AGGREGATE count()', None),
]
def post(body):
    req = urllib.request.Request(URL + "/evaluate", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "X-PrismQL-Client": CLIENT})
    try: return json.load(urllib.request.urlopen(req, timeout=900))
    except urllib.error.HTTPError as e: return json.load(e)
want = set(sys.argv[1:])
for nn, name, construct, sheet, q, d in Q:
    if want and nn not in want: continue
    label = f"cheatsheet-{nn}-{name}"
    print(f"\n## {nn} {construct}\n   label={label}  cheatsheet count: {sheet}\n   {q}")
    base = {"corpus": CORPUS, "query": q, "dictionaries": d or {}}
    if "GROUP BY" in q:
        r = post(base | {"label": label})
        g = r.get("grouped_values")
        if g is None: print("   ERROR", r.get("error") or r); continue
        print(f"   groups = {len(g)}; top:", sorted(g.items(), key=lambda kv: -kv[1])[:5])
        continue
    r = post(base | {"query": q + " AGGREGATE count()"})
    if r.get("error"): print("   ERROR", r["error"]); continue
    print(f"   count = {r.get('value')}  ({r.get('elapsed_ms')} ms)")
    for w in r.get("warnings") or []: print(f"   ! {w.get('code')}: {w.get('message')}")
    r = post(base | {"max_results": 1, "explain": True, "label": label})
    for g in r.get("results", [])[:1]:
        if g.get("bindings"): print("   bindings:", g["bindings"])
        for e in g["events"][:6]:
            print(f"   {e.get('time', '')[:19]}  {e.get('kind', ''):20s} {str(e.get('agent'))[:22]:22s}"
                  f" {(e.get('text') or '')[:160]!r}")
