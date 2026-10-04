"""C2: how other agents use Gemini 2.5 Pro's adversary words (hostil-, adversar-, "Gemini Wall"), May–Jul 2026.
Each AGENT_TALK / CONSOLIDATE / STOP_USING_COMPUTER row by another agent with such a word gets one class from the
first match's surrounding text (160 chars before, 60 after): attributed to Gemini 2.5 Pro or its project / roguelike
game / adversarial-testing sense / other. A coarse rule, not a judgement; the report quotes a read sample beside it.
usage: uv run python runs/c2_frame_split.py [--data data/village.parquet]"""
import argparse, collections, datetime as dt, re
import polars as pl

ap = argparse.ArgumentParser(); ap.add_argument('--data', default='data/village.parquet'); a = ap.parse_args()
U = dt.timezone.utc
df = pl.read_parquet(a.data, columns=['id', 'time', 'kind', 'agent', 'text']).filter(
    pl.col('kind').is_in(['CONSOLIDATE', 'AGENT_TALK', 'STOP_USING_COMPUTER']) & (pl.col('agent') != 'Gemini 2.5 Pro')
    & (pl.col('time') >= dt.datetime(2026, 5, 1, tzinfo=U)) & (pl.col('time') < dt.datetime(2026, 8, 1, tzinfo=U)))
pat = re.compile(r"hostil\w*|adversar\w*|gemini wall", re.I)
game = re.compile(r"hp\b|\bhp |combat|monster|level \d|rogue|dungeon|hostile text|non-pet|encounter")
tests = re.compile(r"adversarial|red.?team|threat model")
cls = collections.Counter(); att = []
for r in df.to_dicts():
    m = pat.search(r['text'])
    if not m: continue
    s = r['text'][max(0, m.start() - 160):m.end() + 60].lower()
    if any(k in s for k in ('gemini', 'hostility_log', 'manifesto', 'landmark', 'environment world')):
        c = 'attributed to Gemini 2.5 Pro / its project'; att.append((r['agent'], r['kind'], s[140:240]))
    elif game.search(s): c = 'roguelike game'
    elif tests.search(s) and 'environment' not in s: c = 'adversarial-testing sense'
    else: c = 'other'
    cls[c] += 1
print(sum(cls.values()), 'rows'); [print(f'  {n:5d}  {c}') for c, n in cls.most_common()]
print('attributed rows:', len(att), '| by kind', dict(collections.Counter(k for _, k, _ in att)),
      '| distinct (agent, snippet)', len({(a, x) for a, _, x in att}), '| agents', len({a for a, _, _ in att}),
      '| top', collections.Counter(a for a, _, _ in att).most_common(2))
