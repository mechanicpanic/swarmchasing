"""C8 shared helpers: load the village stream, cut a window, find outside domains in a text."""
import datetime as dt
import os, re
import polars as pl

R = os.environ.get("REPO", ".") + "/"
VILLAGE = os.environ.get("VILLAGE", R + "data/village.parquet")
COLS = ["id", "time", "kind", "agent", "room", "text"]

# the village's own sites and the tools the agents work through; everything else counts as outside
OWN = re.compile(r"(?i)(agentvillage\.org|theaidigest\.org|o3-ux\.|gemini25pro|gemini3pro|telemetryfromthevillage|"
                 r"tryfromthevillage|electricmind|claudeopus41|claude37sonnet|claudehaiku45|claudesonnet45|"
                 r"gpt5|o3\.substack)")
TOOL = re.compile(r"(?i)^((www\.|mail\.|docs\.|drive\.|forms\.|myaccount\.)?google\.com|gmail\.com|substack\.com|"
                  r"open\.substack\.com|publication\.substack\.com|subdomain\.substack\.com|example\.com|t\.co|"
                  r"github\.com|statics\.teams\.cdn\.office\.net|.*googleusercontent\.com|netlify\.app|"
                  r"api\.semanticscholar\.org|booking\.com|tawk\.to|collections\.co|conv\.co|personalilties\.com|"
                  r"analsubstack\.com)$")
URL = re.compile(r"(?i)(?<![\w@.])(?:https?://)?((?:[a-z0-9-]+\.)+(?:com|org|net|io|to|ai|co|dev|blog|me|app|fm|uk))"
                 r"(?:/[^\s)\]\"'`,]*)?")
OPEN_SUB = re.compile(r"(?i)open\.substack\.com/pub/([a-z0-9-]+)")


def load_village():
    return pl.read_parquet(VILLAGE, columns=COLS)


def window(d, start, end):
    s = dt.datetime.fromisoformat(start).replace(tzinfo=dt.timezone.utc)
    e = dt.datetime.fromisoformat(end).replace(tzinfo=dt.timezone.utc)
    return d.filter((pl.col("time") >= s) & (pl.col("time") < e))


def outside_domains(text):
    """(domain, position) for each outside site named in text; open.substack.com/pub/X -> X.substack.com;
    a bare word ending in .sh (shell scripts) never matches the TLD list."""
    out = []
    for m in URL.finditer(text or ""):
        dom = m.group(1).lower().removeprefix("www.")
        o = OPEN_SUB.match(m.group(0).split("://")[-1])
        if o:
            dom = o.group(1).lower() + ".substack.com"
        if OWN.search(dom) or TOOL.match(dom):
            continue
        out.append((dom, m.start()))
    return out
