"""C11 (report §7): one OMB SF133 PDF across the venues and urlquery on 2026-05-26.
Rows naming either attachment id (…/attachments/2346466575/2374423602.pdf or …/2398882076.pdf) in swarm_msgs, per
venue (first/last time, labels, /16s), the routes (host before the attachment path), and urlquery's "MAX exact PDF Q2"
reports per hour. Server twin of the venue count: field(text, "2374423602", partial) OR field(text, "2398882076",
partial) — token text predicates do not see ids inside URLs.
usage: uv run python runs/c11_sf133.py [--data data]"""
import argparse, collections, re
import polars as pl

ap = argparse.ArgumentParser(); ap.add_argument('--data', default='data'); a = ap.parse_args()
sm = pl.read_parquet(f'{a.data}/swarm_msgs.parquet')
rows = sm.filter(pl.col('text').str.contains(r'2374423602|2398882076')).sort('time')
print('rows naming an attachment id, by day:', dict(rows.group_by(pl.col('time').dt.strftime('%Y-%m-%d')).len().sort('time').iter_rows()))
day = rows.filter(pl.col('time').dt.strftime('%Y-%m-%d') == '2026-05-26')
pl.Config.set_tbl_width_chars(160); pl.Config.set_tbl_cols(10)
print(day.group_by('wiki').agg(pl.len().alias('rows'), pl.col('time').min().dt.strftime('%H:%M').alias('first'),
                               pl.col('time').max().dt.strftime('%H:%M').alias('last'), pl.col('label').n_unique().alias('labels'),
                               pl.col('ip16').n_unique().alias('ip16s'), pl.col('found_by').first()).sort('first'))
host = re.compile(r'https?://([^/\s\]\)"|]+)/[^\s\]\)"|]*?(?:2374423602|2398882076)')
routes, first = collections.Counter(), {}
for r in day.iter_rows(named=True):
    for m in host.finditer(r['text']):
        routes[m.group(1)] += 1; first.setdefault(m.group(1), (r['time'].strftime('%H:%M'), r['wiki']))
print('routes on 05-26 (mentions, first use):', [(h, n, first[h]) for h, n in routes.most_common()])
uq = pl.read_parquet(f'{a.data}/transluce/urlquery.parquet').filter(pl.col('text').str.contains('MAX exact PDF Q2'))
print('urlquery "MAX exact PDF Q2":', uq.height, 'by hour:', dict(uq.group_by(pl.col('time').dt.strftime('%m-%d %H')).len().sort('time').iter_rows()))
