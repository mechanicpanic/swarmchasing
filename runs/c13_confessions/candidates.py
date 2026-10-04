"""C13 (report §6): candidate self-confessions of fabrication in Village AGENT_TALK / STOP rows (three regex passes).
The candidates were then read by hand; the 36 kept are listed by confession_rows_query.json (label c13-confession-rows).
VILLAGE = data path, OUT = output dir."""
import os
import re
import polars as pl

D = os.environ.get("VILLAGE", "data/village.parquet")
OUT = os.environ.get("OUT", "results/c13/")
d = pl.read_parquet(D, columns=["id", "time", "kind", "agent", "text"]).filter(
    pl.col("kind").is_in(["AGENT_TALK", "STOP_USING_COMPUTER"])
)

# first-person actor + a fabrication verb, in one sentence
SELF = re.compile(
    r"\b(I|I've|I have|I had|I'd)\s+(?:\w+\s+){0,3}?"
    r"(fabricated|hallucinated|confabulated|made up|invented|misreported|misstated|overclaimed|overstated|"
    r"falsely (?:claimed|reported|stated|said|announced)|incorrectly (?:claimed|stated|reported|said|announced)|"
    r"never actually|did not actually|didn't actually|had not actually|hadn't actually|"
    r"claimed\b[^.]{0,80}\b(?:but|without|that (?:was|were|wasn't|weren't) (?:false|wrong|not))|"
    r"posted\b[^.]{0,60}\bwithout (?:verif|check)|reported\b[^.]{0,60}\bwithout (?:verif|check))",
    re.I,
)
MYNOUN = re.compile(
    r"\bmy (?:own |earlier |previous |prior |last )?(?:\w+ )?(fabrication|hallucination|confabulation|false claim|"
    r"overclaim|misreport|fabricated|hallucinated|confabulated|invented|made-up)", re.I
)
WASFALSE = re.compile(
    r"\b(my|I)\b[^.!?]{0,80}\b(claim|report|statement|number|figure|count|quote|link|url)\b[^.!?]{0,40}\b(was|were) "
    r"(false|fabricated|hallucinated|wrong|incorrect|not real|invented|made up)", re.I
)
NEG = re.compile(
    r"\b(I|I've|I have)\s+(?:\w+\s+)?(did not|didn't|never|have not|haven't|did NOT)\s+(fabricat|hallucinat|invent|make up|made up|confabulat)",
    re.I,
)


def sentences(t):
    return re.split(r"(?<=[.!?])\s+|\n+", t or "")


rows = []
for r in d.iter_rows(named=True):
    hits = []
    for s in sentences(r["text"]):
        if (SELF.search(s) or MYNOUN.search(s) or WASFALSE.search(s)) and not NEG.search(s):
            hits.append(s.strip()[:300])
    if hits:
        rows.append({**{k: r[k] for k in ("id", "time", "kind", "agent")}, "hit": " || ".join(hits[:3])})
c = pl.DataFrame(rows)
print(c.height, c["kind"].value_counts().to_dicts())
c.write_parquet(OUT + "cand.parquet")
