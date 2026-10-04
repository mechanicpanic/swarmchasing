"""C36 shared loading: recipe detectors, unit saves, page states. See c36.py for the test.
Exclusions (units only): [Admin1], empty labels, the 17 'earlier_revisions_not_published' revisions, saves that add
the Loop broadcast (text_key 146d7f0c0cfc7856), redirect bodies. Page state (what was visible) uses every revision."""
import difflib, gzip, json, os, re
import polars as pl

R = os.environ.get("REPO", ".") + "/"
HUB, BROADCAST = "dse~WillkommenImWiki", "146d7f0c0cfc7856"
REDIR = re.compile(r"(?i)^\s*#(redirect|weiterleitung)")

# One detector per recipe; the same regex runs on a save's added text (use) and on page bodies (visibility).
RECIPES = {
    # proxy / converter hosts wrapped around a source URL
    "jqp.vercel": r"jqp\.vercel\.app",
    "md.succ.ai": r"md\.succ\.ai",
    "markdown.new": r"markdown\.new",
    "allorigins": r"allorigins\.(?:hexlet\.app|win)",
    "r.jina.ai": r"r\.jina\.ai",
    "pure.md": r"(?:^|[^\w.-])pure\.md\b",
    "cors.bwa": r"cors\.bwa\.workers\.dev",
    "counterapi": r"counterapi\.dev",
    "webcrawlerapi": r"webcrawlerapi\.com",
    "translate.goog": r"\.translate\.goog",
    # self-links to the wiki's own pages
    "self uniq=": r"wikiservice\.(?:at|com)/\S*?[?&;]uniq=",
    "self printer view": r"wikiservice\.(?:at|com)/\S*?[?&;](?:template=p|strip=c)\b",
    # June 18 page templates (heading line)
    "= DZFASTMD": r"(?m)^= ?DZFASTMD",
    "= Agent Unique Web Links": r"(?m)^= ?Agent Unique Web Links",
    "= SEC county variants": r"(?m)^= ?SEC county variants",
    "= Investor Official Pretty": r"(?m)^= ?Investor Official Pretty County Data",
    "= ZULUMD TAKEOVER": r"(?m)^= ?ZULUMD TAKEOVER",
    "= SEC MD Direct Source": r"(?m)^=+ ?SEC MD Direct Source",
    # June 16 relay wording
    "if you are ahead": r"(?i)if you are ahead",
    "append only": r"(?i)\bappend only\b",
    "task-clock": r"(?i)\btask[- ]clock\b",
}
GROUP = {k: ("host" if i < 10 else "self" if i < 12 else "template" if i < 18 else "relay")
         for i, k in enumerate(RECIPES)}
CRE = {k: re.compile(v) for k, v in RECIPES.items()}


def load_revs():
    rows = []
    for l in gzip.open(R + "data/collusion_wiki/revisions.jsonl.gz", "rt"):
        r = json.loads(l)
        rows.append({"rev": r["rev_id"], "page": r["page_key"], "seq": int(r["seq"]), "label": r["label"] or "",
                     "t": r["time"], "body": r["body"] or "", "summary": r.get("change_summary"),
                     "unpub": r.get("diff_base_reason") == "earlier_revisions_not_published"})
    df = pl.DataFrame(rows).with_columns(pl.col("t").str.to_datetime("%Y-%m-%dT%H:%M:%SZ", time_zone="UTC"))
    return df.with_columns(pl.col("t").dt.epoch("s").alias("s")).sort(["s", "page", "seq"])


def load_adds():
    m = pl.read_parquet(R + "data/wiki_msgs.parquet", columns=["rev", "label", "page", "time", "kind", "text", "text_key"])
    return m.filter(pl.col("kind") == "add")


def unit_saves(revs, adds):
    """One row per eligible save with its added text joined; excluded saves dropped."""
    bc = set(adds.filter(pl.col("text_key") == BROADCAST)["rev"].to_list())
    txt = adds.group_by("rev").agg(pl.col("text").str.join("\n").alias("added"))
    s = revs.join(txt, on="rev", how="inner")
    return s.filter((pl.col("label") != "") & (pl.col("label") != "[Admin1]") & ~pl.col("unpub")
                    & ~pl.col("rev").is_in(list(bc)) & ~pl.col("body").str.contains(REDIR.pattern))




def line_owners(revs):
    """rev -> [(line, owner label)] for the body lines that match any recipe. The owner is the label of the save that
    inserted the line; lines kept unchanged across a save (difflib line diff against the page's previous body) keep
    their owner. Used to ignore the focal label's own text when asking what a page showed it."""
    out = {}
    for (pg,), g in revs.sort(["s", "seq"]).group_by(["page"], maintain_order=True):
        prev, own = [], []
        for rv, lab, body in g.select("rev", "label", "body").iter_rows():
            cur = body.split("\n"); new = [lab] * len(cur)
            sm = difflib.SequenceMatcher(None, prev, cur, autojunk=False)
            for tag, a0, a1, b0, b1 in sm.get_opcodes():
                if tag == "equal": new[b0:b1] = own[a0:a1]
            out[rv] = [(x.strip(), o) for x, o in zip(cur, new) if any(c.search(x) for c in CRE.values())]
            prev, own = cur, new
    return out
