"""collusion.wiki explorer → the sites the download does not carry (community-found pastebins, wikis, shorteners,
rubygems): one row per version of each record page, with its time, site and the lines it added or removed.
Aleph's word 2026-10-02: reading the public explorer is fine (the site logs every visitor's IP publicly).
Step 1 `fetch`: site indexes and record pages into data/collusion_explorer/ (cached; 1.5 s between requests).
Step 2 `parse`: → data/explorer_sites_rows.parquet (then `prismql ingest table … --id id --time time --sort seq`).
Skipped: dse/probier/fractal/dorfwiki (in the download with labels) and rmn.re (its full log is in shortener-logs)."""

import collections
import hashlib
import html
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://collusion.wiki/explorer/"
OUT = pathlib.Path("data/collusion_explorer")
HAVE = {"dse", "probier", "fractal", "dorfwiki", "rmn.re"}


def get(url, path):
    if path.exists() and path.stat().st_size:
        return path.read_text()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    body = urllib.request.urlopen(req, timeout=30).read().decode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    time.sleep(1.5)
    return body


def sites():
    index = get(BASE + "sites/", OUT / "sites.html")
    names = re.findall(r'href="([^"./#][^"]*)"', index)
    return [s for s in dict.fromkeys(names) if s not in HAVE and "/" not in s]


def found_by():
    # the sites index says who found each venue; community finds came after the report (2026-09-04), when fake posts
    # also appeared — their untimed rows cannot be dated and are unverified
    index = get(BASE + "sites/", OUT / "sites.html")
    out = {}
    for site, row in re.findall(
        r'<a class="row" href="([^"]+)"(.*?)</a>', index, re.DOTALL
    ):
        row = re.sub(r"\s+", " ", text(row))
        who = re.search(r"reported by (.+?)\s*$", row)
        out[site] = "community: " + who.group(1) if who else "report authors"
    return out


def record_keys(site):
    # a long site index is split into site, site~2, site~3 … (250 records each)
    keys, todo, seen = [], [site], set()
    while todo:
        name = todo.pop(0)
        seen.add(name)
        page = get(BASE + "sites/" + name, OUT / "sites" / (name + ".html"))
        keys += re.findall(r'href="\.\./page/([^"]+)"', page)
        more = re.findall(rf'href="({re.escape(site)}~\d+)"', page)
        todo += [m for m in more if m not in seen and m not in todo]
    return list(dict.fromkeys(keys))


def page_path(k):
    # shortener codes are case-sensitive, the macOS file system is not: keys equal up to case get a hash suffix
    if k.lower() in CASE_TWINS:
        k += "--" + hashlib.sha1(k.encode()).hexdigest()[:8]
    return OUT / "page" / (k + ".html")


CASE_TWINS = set()


def all_keys():
    keys = [(s, k) for s in sites() for k in record_keys(s)]
    low = collections.Counter(k.lower() for _, k in keys)
    CASE_TWINS.update(k for k, n in low.items() if n > 1)
    return keys


def fetch():
    keys = all_keys()
    for i, (_, k) in enumerate(keys, 1):
        try:
            get(
                BASE + "page/" + urllib.parse.quote(k, safe="~@"),
                page_path(k),
            )
        except (OSError, ValueError) as e:  # one missing page should not stop the rest
            print("FAIL", k, e, flush=True)
        if i % 50 == 0:
            print(f"{i}/{len(keys)}", flush=True)
    print("records:", len(keys))


ENTRY = re.compile(r'<li class="entry"(.*?)</li>', re.DOTALL)
ATTR = re.compile(r'data-([a-z-]+)="([^"]*)"')
# a line ends at the </span> that closes the <p>/<div> or precedes the next line (lines nest withheld-URL spans)
LINE = re.compile(
    r'data-testid="(added|removed|folded)-line">(.*?)</span>(?=\s*(?:<span data-testid=|</p>|</div>))',
    re.DOTALL,
)
SHARED = re.compile(r'<a class="url" href="\.\./url/([0-9a-f]+)">')


def text(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def parse():
    import polars as pl
    from textkey import key

    by = found_by()
    rows = []
    for s, k in all_keys():
        p = page_path(k)
        if not p.exists():
            continue
        doc = p.read_text()
        chunks = re.search(r'data-chunks="(\d+)"', doc)
        if chunks and int(chunks.group(1)) > 1:
            print("more chunks than fetched:", k, chunks.group(1))
        shared = list(dict.fromkeys(SHARED.findall(doc.split('id="thread"')[0])))
        for e in ENTRY.findall(doc):
            a = dict(ATTR.findall(e.split(">", 1)[0]))
            src = re.search(r'class="sources">(.*?)</p>', e, re.DOTALL)
            flag = re.search(r'class="flag">(.*?)</span>', e)
            lines = [("added" if d == "folded" else d, x) for d, x in LINE.findall(e)]
            for kind in ("added", "removed"):
                t = "\n".join(text(x) for d, x in lines if d == kind).strip()
                if t:
                    rows.append(
                        {
                            "id": f"{a.get('rev-id')}:{kind[:-1] if kind == 'added' else 'remove'}",
                            "site": s,
                            "page": k,
                            "rev": a.get("rev-id"),
                            "rev_seq": int(a.get("seq") or 0),
                            "time": a.get("time") or None,
                            "time_grade": a.get("grade"),
                            "kind": "add" if kind == "added" else "remove",
                            "text": t,
                            "sources": text(src.group(1)).strip() if src else None,
                            "flag": flag.group(1) if flag else None,
                            "found_by": by.get(s),
                            "shared_urls": shared,
                        }
                    )
    df = (
        pl.DataFrame(rows, infer_schema_length=None)
        .with_columns(pl.col("time").str.to_datetime(time_zone="UTC"))
        .sort("time", "page", "rev_seq", "kind", nulls_last=True)
        .with_row_index("seq")
        .with_columns(
            pl.col("text").map_elements(key, return_dtype=pl.Utf8).alias("text_key")
        )
    )
    assert df["id"].is_unique().all()
    df.write_parquet("data/explorer_sites_rows.parquet")
    print(df.height, "rows;", df["time"].null_count(), "without time")
    print(
        df.group_by("site")
        .agg(
            pl.len(),
            pl.col("time").min().alias("first"),
            pl.col("time").max().alias("last"),
            pl.col("time").null_count().alias("no_time"),
        )
        .sort("len", descending=True)
    )


if __name__ == "__main__":
    {"fetch": fetch, "parse": parse}[sys.argv[1]]()
