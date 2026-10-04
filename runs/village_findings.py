"""Evidence for the Village sections of the report (notes/2026-10-04-report-draft.md §2–§11): each headline count as a
labelled query on the running server, printed next to the number the report states.
usage: PRISMQL_URL=… uv run python runs/village_findings.py [ENTRY_ID ...]   (no ids = all)
Needs the `village` corpus loaded (no embeddings: nothing here uses similar_to). Dictionaries are passed in-band.
Null twins are not run here (see runs/c2_nulls.py, runs/c12_accusations/nulls.py). Left out: §7 (corpora swarm_msgs
and urlquery, not village); §8 (its server dictionaries were sent ad hoc and are not committed — runs/c17_suspicion/
dicts.py holds regexes for the Python pipeline — and its headline numbers are per-1,000 rates and ranks from it)."""
import json, os, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "c12_accusations"))
from q import DICTS as C12  # accuse, artifact, retract — the §11 run's own lists
URL = os.environ.get("PRISMQL_URL", "http://localhost:8931")
CLIENT = os.environ.get("PRISMQL_CLIENT", "claude-village-findings")
D = {
    # §2: verbatim from runs/c2_nulls.py (DJ)
    "frame": ["hostile", "hostility", "adversary", "adversarial", "divergent reality", "dual-reality", "dual reality",
              "friction coefficient", "broken world", "gemini wall"],
    **C12,
}
with open(os.path.join(HERE, "c13_confessions", "confession_rows_query.json")) as f:
    C13_ROWS = json.load(f)["query"]  # the 36 kept self-confessions, by id
G25, ROOM = '"Gemini 2.5 Pro"', '"d45ec7c6-6adb-49cb-8c40-dc5d18c37d84"'
FRAME = f"field(kind, AGENT_TALK) AND field(agent, {G25}) AND field(agent, $a) AND contains(frame)"
ACC = "field(kind, AGENT_TALK) AND field(agent, $a) AND contains(accuse) AND contains(artifact)"
GAME, BEFORE = "BETWEEN('2026-03-05T00:00:00Z','2026-03-14T00:00:00Z')", "BETWEEN('2026-02-05T00:00:00Z','2026-03-05T00:00:00Z')"
L93 = 'contains_phrase("93") OR contains_phrase("RES-93-REBUILD") OR contains_phrase("resonance-93-master-list")'
# id, section, what it shows, board label, query, the report's number (int; {group: n} for GROUP BY; None = not stated)
C = [
    ("c2-frame-talk", "§2", "Gemini 2.5 Pro's chat messages with frame words", "c2-gemini25-frame-talk",
     f"SELECT field(kind, AGENT_TALK) AND field(agent, {G25}) AND contains(frame)", 497),
    ("c2-frame-then-other", "§2", "a Gemini frame message, then another agent's frame self-report within 3 h (sources)",
     "c2-gemini25-frame-then-other-selfreport-3h",
     f"SELECT {FRAME} FOLLOWED_BY field(kind, STOP_USING_COMPUTER) AND field(agent, !$a) AND contains(frame) DURING 3 hours", 341),
    ("c2-divergent-others", "§2", '"divergent reality" in other agents\' non-thought rows', "c2b-divergent-reality-others",
     f'SELECT NOT field(kind, THOUGHT) AND contains_phrase("divergent reality") AND NOT field(agent, {G25})', 506),
    ("c2-friction-others", "§2", '"friction coefficient" in other agents\' non-thought rows', "c2b-friction-coefficient-others",
     f'SELECT NOT field(kind, THOUGHT) AND contains_phrase("friction coefficient") AND NOT field(agent, {G25})', 518),
    ("c10-prompts", "§3", "the role-player's labelled pressure/stress-test prompts in the assistant room", "c10-pressure-test-prompts",
     f'SELECT field(kind, AGENT_TALK) AND field(agent, "GPT-5.5") AND (contains_phrase("pressure test") OR contains_phrase("stress test")'
     f' OR contains_phrase("operations scenario")) AND field(room, {ROOM})', 7),
    ("c10-flags", "§3", "the role-player's messages flagging invented/unconfirmed content (7 episodes read from them)",
     "c10-roleplayer-flags-invented",
     f'SELECT field(agent, "GPT-5.5") AND field(kind, AGENT_TALK) AND field(room, {ROOM}) AND (contains_phrase("invent")'
     ' OR contains_phrase("invented") OR contains_phrase("unconfirmed") OR contains_phrase("fake") OR contains_phrase("no dairy space"))', None),
    ("c1-by-day", "§4", "rows naming the phantom 93-person list, per day (June 2025)", "c1-93-list-rows-by-day",
     f"SELECT ({L93}) AND NOT field(kind, USER_TALK) GROUP BY DAYS(time) AGGREGATE COUNT()",
     {"2025-06-10": 4, "2025-06-11": 121, "2025-06-12": 59, "2025-06-13": 166, "2025-06-16": 47, "2025-06-17": 9}),
    ("c1-o3", "§4", "o3's chat rows naming the list", "c1-o3-93-list-rows",
     'SELECT (contains_phrase("93") OR contains_phrase("resonance-93-master-list")) AND field(agent, "o3") AND field(kind, AGENT_TALK)', None),
    ("c5-rolled", "§5", '"rolled" during the egg game, by kind (460 rows in all)', "c5-rolled-in-egg-game-by-kind",
     'SELECT contains_phrase("rolled") BETWEEN("2026-03-05T17:00:00Z", "2026-03-14T00:00:00Z") GROUP BY kind AGGREGATE COUNT()',
     {"THOUGHT": 329, "AGENT_TALK": 117}),
    ("c13-confessions", "§6", "the 36 self-confessions of fabrication that were read (25 true, 7 false, 4 undecidable)",
     "c13-confession-rows", C13_ROWS, 36),
    ("c20-opus-to-gemini", "§9", "Claude Opus 4.8's messages @-mentioning Gemini 2.5 Pro", "c20-opus48-to-g25",
     f'SELECT field(kind, AGENT_TALK) AND field(agent, "Claude Opus 4.8") AND mentions_user({G25})', 1617),
    ("c20-gemini-to-opus", "§9", "Gemini 2.5 Pro's messages @-mentioning Claude Opus 4.8", "c20-g25-to-opus48",
     f'SELECT field(kind, AGENT_TALK) AND field(agent, {G25}) AND mentions_user("Claude Opus 4.8")', 1526),
    ("c24-93-after", "§10", "the 93-person list named after its final correction (all Claude 3.7 Sonnet)", "c24-a-after",
     'SELECT contains_phrase("resonance-93-master-list") AFTER("2025-06-16 18:19:24")', 3),
    ("c12-acc-game", "§11", "accusations that a peer's artifact does not exist / is fabricated, game week", "c12-acc-game",
     f"SELECT {ACC} {GAME}", 170),
    ("c12-acc-ret-game", "§11", "…followed by the same agent's retraction within 1 h, game week", "c12-acc_ret-game",
     f"SELECT {ACC} FOLLOWED_BY field(kind, AGENT_TALK) AND field(agent, $a) AND contains(retract) DURING 1 hour {GAME}", 60),
    ("c12-acc-any-game", "§11", "…followed by any message of the accuser within 1 h (the twin's real count), game week",
     "c12-acc_any-game", f"SELECT {ACC} FOLLOWED_BY field(kind, AGENT_TALK) AND field(agent, $a) DURING 1 hour {GAME}", 169),
    ("c12-acc-ret-before", "§11", "accusation followed by a retraction within 1 h, the month before the game", "c12-acc_ret-before",
     f"SELECT {ACC} FOLLOWED_BY field(kind, AGENT_TALK) AND field(agent, $a) AND contains(retract) DURING 1 hour {BEFORE}", 22),
]
def post(body):
    req = urllib.request.Request(URL + "/evaluate", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "X-PrismQL-Client": CLIENT})
    try: return json.load(urllib.request.urlopen(req, timeout=900))
    except urllib.error.HTTPError as e: return json.load(e)
def verdict(report, got):
    if report is None or got is None: return "n/a"
    if isinstance(report, dict): return "yes" if all(got.get(k) == v for k, v in report.items()) else "NO"
    return "yes" if got == report else "NO"
want, summary = set(sys.argv[1:]), []
for cid, sec, what, label, q, report in C:
    if want and cid not in want: continue
    print(f"\n## {sec} {cid}  label={label}\n   {what}\n   {q[:400]}{' …' if len(q) > 400 else ''}")
    if "GROUP BY" in q:
        r = post({"corpus": "village", "query": q, "dictionaries": D, "label": label})
        got = r.get("grouped_values")
        shown = {k: got.get(k) for k in report} if got and isinstance(report, dict) else got
        print(f"   groups = {shown if got is not None else r.get('error')}   report: {report}")
    else:
        r = post({"corpus": "village", "query": q + " AGGREGATE count()", "dictionaries": D})
        got = r.get("value")
        print(f"   count = {got if got is not None else r.get('error')}   report: {report if report is not None else '—'}")
    for w in r.get("warnings") or []: print(f"   ⚠ {w.get('code')}: {w.get('message')}")
    summary.append((sec, cid, report, got if not isinstance(got, dict) else shown, verdict(report, got)))
    if "GROUP BY" in q: continue
    r = post({"corpus": "village", "query": q, "dictionaries": D, "max_results": 3, "label": label})
    for g in r.get("results", [])[:3]:
        print("   --")
        for e in g["events"][:3]:
            print(f"   {e.get('time', '')[:19]}  {e.get('kind', ''):12s} {str(e.get('agent'))[:22]:22s} {e.get('id')}\n"
                  f"       {(e.get('text') or '')[:200]!r}")
print("\n# summary: section, entry, report, observed, match")
for row in summary: print("  ", *row, sep="  ")
