# PrismQL — sequence queries over event logs

PrismQL is installed in this environment (Python package `prismql`). It answers questions about **order** in a
stream of events: "A, then B within 10 minutes, by the same actor", "A never followed by B", "three of X in a row",
with counts and the matching groups of events. The full language is in `/opt/prismql/LANGUAGE_REFERENCE.md`.

## Load rows as a stream

```python
from prismql import PrismQLEngine
from prismql.backends.memory import MemoryBackend

# any list of dicts with scalar fields; here a made-up forum log
docs = [
    {"id": "e1", "time": "2026-01-01T10:00:00Z", "kind": "post",   "user": "ann", "thread": "t1"},
    {"id": "e2", "time": "2026-01-01T10:02:00Z", "kind": "reply",  "user": "bob", "thread": "t1"},
    {"id": "e3", "time": "2026-01-01T10:03:00Z", "kind": "post",   "user": "bob", "thread": "t2"},
    {"id": "e4", "time": "2026-01-01T11:30:00Z", "kind": "reply",  "user": "ann", "thread": "t2"},
    {"id": "e5", "time": "2026-01-01T11:31:00Z", "kind": "remove", "user": "mod", "thread": "t1"},
]
docs.sort(key=lambda d: d["time"])            # the stream's order is the load order
by_id = {d["id"]: d for d in docs}
eng = PrismQLEngine(search_backend=MemoryBackend(docs, id_field="id"), timestamp_field="time")
```
For a JSONL file: `docs = [json.loads(line) for line in open(path)]`, drop or flatten list/dict fields
(`{k: v for k, v in d.items() if not isinstance(v, (list, dict))}`), then sort by the time field. Several tables can
be one stream: concatenate their rows (give each a field saying which table it came from) and sort by time.

## Ask

```python
q = "SELECT field(kind, post) AND field(thread, $t) AND field(user, $u) FOLLOWED_BY field(kind, reply) AND field(thread, $t) AND field(user, !$u) DURING 10 minutes"
print(eng.execute(q + " AGGREGATE count()").to_dict())   # {'function': 'count', 'value': 1}: e1 -> e2
for g in eng.execute(q):                                   # groups, each a list of event ids
    print([(by_id[i]["time"], by_id[i]["user"], by_id[i]["kind"]) for i in g])
print(eng.execute("SELECT field(kind, reply) GROUP BY user AGGREGATE count()").to_dict())
```

Building blocks (see the reference for all of them):
- `field(name, value)` matches a field; `field(name, $x)` binds a variable, so the same `$x` in a later leg means
  "the same value"; `field(name, !$x)` means "a different value".
- `A FOLLOWED_BY B DURING 1 hour` (time window) or `INWINDOW n` (n events); `A NOT_FOLLOWED_BY B DURING …`.
- `contains(word)` for text fields; `AND`, `OR`, `NOT` inside a leg.
- `AGGREGATE count()`, `GROUP BY field`.

## Reading a count
A count of "A then B" is high in a busy stream by chance alone. To see whether the order matters, shuffle the
times of the B events (e.g. within each day) a few dozen times, re-run the same query, and compare the real count with
the shuffled ones.
