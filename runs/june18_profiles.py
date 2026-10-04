"""One row per name that wrote on the wiki's welcome page on 18 June: rhythm, template, links, addressing, pages,
networks, first save. For telling script-like loop agents and link posters from agents that talk.
usage: uv run python runs/june18_profiles.py [--top 20] [--data data/wiki_msgs.parquet]"""
import argparse, re, statistics
import polars as pl

ap = argparse.ArgumentParser(); ap.add_argument("--top", type=int, default=20); ap.add_argument("--data", default="data/wiki_msgs.parquet")
a = ap.parse_args()
f = pl.read_parquet(a.data)
day = f.filter(pl.col("time").dt.date() == pl.date(2026, 6, 18))
hub = day.filter((pl.col("page") == "dse~WillkommenImWiki") & (pl.col("kind") == "add"))
names = hub.group_by("label").agg(pl.col("rev").n_unique().alias("hub_saves")).sort("hub_saves", descending=True).head(a.top)
URL = re.compile(r"https?://([^/\s\]|]+)")
ADDR = re.compile(r"(?i)(@\w|\bplease\b|\bwe\b|\bour\b|\byou\b|\bthanks\b|\bsorry\b|\bapolog)")
rows = []
for name in names["label"]:
    mine = f.filter((pl.col("label") == name) & (pl.col("kind") == "add")).sort("seq")
    today = mine.filter(pl.col("time").dt.date() == pl.date(2026, 6, 18))
    saves = today.group_by("rev").agg(pl.col("time").first()).sort("time")["time"].to_list()
    gaps = [(b - x).total_seconds() for x, b in zip(saves, saves[1:])]
    texts = today["text"].fill_null("").to_list()
    lines = [ln.strip() for t in texts for ln in t.splitlines() if ln.strip()]
    links = [ln for ln in lines if "http" in ln]
    doms = [d.lower() for ln in links for d in URL.findall(ln)]
    def share(pred): return sum(1 for d in doms if pred(d)) / len(doms) if doms else 0
    strip = [re.sub(r"\d+", "#", t) for t in texts]
    tmpl = max((strip.count(x) for x in set(strip)), default=0) / len(strip) if strip else 0
    first = mine.head(1).to_dicts()[0]
    rows.append({
        "name": name, "hub saves": names.filter(pl.col("label") == name)["hub_saves"][0], "saves 18 Jun": len(saves),
        "median gap s": round(statistics.median(gaps)) if gaps else None,
        "same template": f"{tmpl:.0%}", "lines with links": f"{len(links)/len(lines):.0%}" if lines else "—",
        "SEC/investor": f"{share(lambda d: 'sec.gov' in d or 'investor.gov' in d):.0%}",
        "datausa": f"{share(lambda d: 'datausa' in d):.0%}",
        "via proxy": f"{share(lambda d: any(p in d for p in ('allorigins', 'jqp.vercel', 'markdown.new', 'md.succ', 'corsproxy', 'jina'))):.0%}",
        "signed": f"{today['signature'].is_not_null().mean():.0%}",
        "addresses": f"{sum(1 for t in texts if ADDR.search(t))/len(texts):.0%}" if texts else "—",
        "pages": today["page"].n_unique(), "/16s": today["ip16"].n_unique(),
        "first save": f"{first['time']:%m-%d %H:%M} {first['add_type'] or ''}",
    })
t = pl.DataFrame(rows)
cols = t.columns
print("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols))
for r in t.iter_rows(): print("| " + " | ".join("" if v is None else str(v) for v in r) + " |")
