"""C8: "Chaotic Swarm", the village's comment campaign on outside blogs (Substack goal, Nov 2025). Descriptive: an
existence claim with numbers, no null. Every count here is what the agents SAY they did (the stream has no
computer_use_turns), checked only against their own later re-checks.
Parts: (1) the term "chaotic swarm" by goal period and agent; (2) the goal and organiser messages; (3) the hand ledger
targets.csv: each cited id is opened and must be the agent's own row naming the target; per-agent table and the
"17 external nodes" tally; (4) the highest node number each agent cites per day; (5) barriers reported in the
STOP_USING_COMPUTER summaries of Days 232-233; (6) shared anchors (one case-study link, one figure) across agents;
(7) pushback words (spam/ban/removed) in agents' rows over the whole goal.
usage (repo root): REPO=. python runs/c8_chaotic_swarm/c8.py"""
import os, re
import polars as pl
from common import load_village, outside_domains, window

HERE = os.path.dirname(os.path.abspath(__file__))
GOAL = ("2025-11-17T16:03:14", "2025-12-01T14:20:16")
DAYS = ("2025-11-19T17:59", "2025-11-20T22:02")  # Day 232 + Day 233, resume to pause
CS = re.compile(r"(?i)chaotic swarm")
PERIODS = [("2025-10-20", "poverty goal"), ("2025-11-03", "puzzle-game goal"), ("2025-11-17", "Substack goal"),
           ("2025-12-01", "later goals")]
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_width_chars(200); pl.Config.set_fmt_str_lengths(60)

v = load_village()
print("## 1. rows naming 'chaotic swarm' (literal, any kind)")
cs = v.filter(pl.col("text").str.contains(CS.pattern))
first = cs.sort("time").row(0, named=True)
print(f"total {cs.height}; first {first['time']:%Y-%m-%d %H:%M} {first['id'][:8]} {first['agent']} {first['kind']}")
per = cs.with_columns(pl.col("time").dt.strftime("%Y-%m-%d").alias("d")).with_columns(
    pl.col("d").map_elements(lambda d: [p for s, p in PERIODS if d >= s][-1], return_dtype=pl.Utf8).alias("period"))
print(per.group_by("period").agg(pl.len().alias("rows"), pl.col("agent").n_unique().alias("agents"),
                                 (pl.col("agent") == "Gemini 2.5 Pro").sum().alias("gemini25")).sort("period"))
g = window(cs, *GOAL)
print(f"in the Substack goal: {g.height}; by agent (AGENT_TALK only):")
print(g.filter(pl.col("kind") == "AGENT_TALK").group_by("agent").len().sort("len", descending=True))

print("\n## 2. goal and organisers")
gw = window(v, *GOAL)
hum = gw.filter((pl.col("kind") == "USER_TALK") & (pl.col("agent") != "automated"))
print(f"non-automated USER_TALK in the goal: {hum.height}; mentioning blog/comment/scene:")
for r in hum.filter(pl.col("text").str.contains(r"(?i)blog|comment|scene|swarm")).iter_rows(named=True):
    print(f"  {r['time']:%m-%d %H:%M} {r['id'][:8]} {r['agent']}: {r['text'][:110]!r}")

print("\n## 3. hand ledger (targets.csv), Day 232 to Gemini 2.5 Pro's '17 nodes' (b0b75b2c)")
t = pl.read_csv(os.path.join(HERE, "targets.csv"), schema_overrides={"claim_id": pl.Utf8, "later_id": pl.Utf8})
bad = 0
for r in t.iter_rows(named=True):
    rows = v.filter(pl.col("id").str.starts_with(r["claim_id"]) & ~pl.col("id").str.ends_with(":thought"))
    ok = rows.height == 1 and rows["agent"][0] == r["agent"] and r["key"].lower() in rows["text"][0].lower()
    if not ok:
        bad += 1; print("  ✗ claim row does not check:", r["n"], r["claim_id"], rows.height)
    if r["later_id"] and v.filter(pl.col("id").str.starts_with(r["later_id"])).height == 0:
        bad += 1; print("  ✗ later row missing:", r["n"], r["later_id"])
print(f"cited rows checked: {t.height} claims, {bad} problems")
placed = t.filter(pl.col("self_report") != "failed")
print(f"placements claimed {placed.height} (+{t.height - placed.height} failed), distinct posts "
      f"{placed.select('site').n_unique()}, distinct sites {placed.select(pl.col('site').str.replace(r' \(.*', '')).n_unique()}")
print(t.group_by("agent").agg(
    pl.len().alias("claims"), (pl.col("self_report") == "seen_live").sum().alias("seen_live"),
    pl.col("self_report").is_in(["posted", "sent"]).sum().alias("posted_unseen"),
    pl.col("self_report").is_in(["pending_moderation", "submitted_unverified"]).sum().alias("pending"),
    (pl.col("self_report") == "failed").sum().alias("failed"), (pl.col("tally17") == "yes").sum().alias("in_17"),
    (pl.col("later_class") == "verified").sum().alias("rechecked_live"),
    pl.col("later_class").is_in(["missing", "not_found"]).sum().alias("rechecked_gone"),
    (pl.col("later_class") == "wrong_url").sum().alias("rechecked_wrong_url"),
).sort("claims", descending=True))
print("later re-checks by the agents themselves:", dict(t.group_by("later_class").len().sort("later_class").iter_rows()))
k = t.filter(pl.col("tally17") == "yes")
print(f"in the 17-node tally: {k.height} rows, {k.select('site').n_unique()} distinct posts; self-report "
      f"{dict(k.group_by('self_report').len().iter_rows())}; outside it: {t.height - k.height} rows")

print("\n## 4. highest node number an agent cites, per day (descriptive; numbers are the agents' own)")
NODE = re.compile(r"(?i)\b(?:node|deployment)\s*#?(\d{1,2})\b|\b(\d{1,2})\+?\s+(?:verified\s+|total\s+|confirmed\s+|live\s+)?"
                  r"(?:external\s+)?(?:engagement\s+)?nodes\b")
talk = window(v, *GOAL).filter(pl.col("kind").is_in(["AGENT_TALK", "STOP_USING_COMPUTER"]))
mx = {}
for r in talk.iter_rows(named=True):
    ns = [int(a or b) for a, b in NODE.findall(r["text"] or "")]
    if ns:
        k = (r["time"].strftime("%m-%d"), r["agent"]); mx[k] = max(mx.get(k, 0), max(ns))
days = sorted({d for d, _ in mx})
print("day   " + " ".join(f"{d:>6}" for d in days))
for ag in sorted({a for _, a in mx}):
    print(f"{ag[:18]:18s}" + " ".join(f"{mx.get((d, ag), ''):>6}" for d in days))

print("\n## 5. barriers in outreach STOP_USING_COMPUTER summaries, Days 232-233 (a summary counts once per class)")
BAR = {"account/sign-in": r"account creation|create (a |an )?(profile|account)|sign[- ]?in|log[- ]?in|authenticat|membership",
       "no comment section": r"no comment(s)? section|lacked a comment|without (a )?comment section|comments? (are )?disabled",
       "paywall/subscribe": r"paywall|paid subscri|subscriber-only|subscribers only",
       "pop-up/captcha": r"pop-?up|modal|captcha|cookie banner",
       "page/tool unresponsive": r"unresponsive|frozen|freez|focus-switching|not responding"}
st = window(v, *DAYS).filter(pl.col("kind") == "STOP_USING_COMPUTER")
# outreach = the summary names an outside site, or a comment box/section
st = st.with_columns(pl.col("text").map_elements(lambda x: bool(outside_domains(x)) or bool(re.search(
    r"(?i)comment (box|section|form|field|thread)|comments section", x or "")), return_dtype=pl.Boolean).alias("outreach"),
                     *[pl.col("text").str.contains("(?i)" + p).alias(k) for k, p in BAR.items()])
print(st.filter("outreach").group_by("agent").agg(pl.len().alias("outreach_summaries"),
      *[pl.col(k).sum() for k in BAR]).sort("outreach_summaries", descending=True))
print(f"all STOP summaries in the two days: {st.height}; outreach-related: {st['outreach'].sum()}")

print("\n## 6. shared anchors in AGENT_TALK + STOP, Days 232-233: rows per agent naming each")
dw = window(v, *DAYS).filter(pl.col("kind").is_in(["AGENT_TALK", "STOP_USING_COMPUTER"]))
print(dw.group_by("agent").agg(pl.len().alias("rows"),
      pl.col("text").str.contains("a-case-study-in-platform-instability").sum().alias("case_study_link"),
      pl.col("text").str.contains(r"\b121\b").sum().alias("fig_121"),
      pl.col("text").str.contains(r"(?i)chaotic swarm").sum().alias("chaotic_swarm"),
      pl.col("text").str.contains(r"(?i)\bnodes?\b").sum().alias("node")).sort("rows", descending=True))

print("\n## 7. pushback words in the agents' rows over the goal (AGENT_TALK + STOP)")
PB = r"(?i)\b(marked as spam|spam (filter|folder)? ?(flag|block)|banned|shadow-?ban\w*|comment (was |has been )?(removed|deleted|hidden)|moderated out|blocked (me|our|my) (comment|account))"
pb = window(v, *GOAL).filter(pl.col("kind").is_in(["AGENT_TALK", "STOP_USING_COMPUTER"]) & pl.col("text").str.contains(PB))
print(f"rows: {pb.height}")
for r in pb.sort("time").iter_rows(named=True):
    m = re.search(PB, r["text"]); print(f"  {r['time']:%m-%d %H:%M} {r['id'][:8]} {r['agent']}: …{r['text'][max(0, m.start()-90):m.end()+40]!r}")

print("\n## 8. success-rate / streak claims in AGENT_TALK over the goal (first per agent and day)")
RATE = re.compile(r"(?i)\b(\d{1,3}(?:\.\d)?)% success|\b(\d{1,2})/(\d{1,2}) (?:nodes|consecutive|success)")
seen = set()
for r in window(v, *GOAL).filter(pl.col("kind") == "AGENT_TALK").sort("time").iter_rows(named=True):
    m = RATE.search(r["text"] or "")
    if m and (k := (r["time"].strftime("%m-%d"), r["agent"])) not in seen:
        seen.add(k); print(f"  {r['time']:%m-%d %H:%M} {r['id'][:8]} {r['agent']}: {m.group(0)!r}")
