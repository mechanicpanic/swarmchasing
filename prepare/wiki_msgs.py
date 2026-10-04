"""collusion.wiki export → one stream of what each save ADDED or REMOVED, plus page deletes, probes and recreations.
A revision body is the whole page (graph @aleph/prismql, node #160); the export's `hunks` say which lines a save
changed (indices into body.split("\n"), checked equal to `lines` on all 14,591 revisions), so one row per hunk is one
message-sized change with its author label, network and time.
kind: add (insert/replace, new text) · remove (delete/replace, text taken from the base revision) · delete (admin page
delete) · probe (scripted request, no save) · revert (save recreating a deleted page).
text_key: hash of the normalised text; first_of_text marks its first appearance in the stream (copy vs new message);
author_label on remove rows: whose text was removed — for each removed line, the label of the latest earlier save on
the same page that added that line; the label most of the lines point to (null when no earlier save holds them, e.g.
text from before the published cut). Line by line, because a save often removes one line of a block another save added.
by_other: the remover is not that author (null when the author is unknown).
add_type: new | copy (text seen before, never on this page) | readd (already added on this page: restore, edit war,
recreation). An edited line is a new text and counts as `new` under the editor — authorship of a line is who last
shaped it, not who first wrote its words.
signature: the name on the last line of the text that ends in "-- Name" (null if none) — compare with label to see a
save signed by another name than the one it was saved under.
Output: data/wiki_msgs_rows.parquet (then `prismql ingest table … --id id --time time --sort seq`)."""

import gzip
import json
import re
from collections import Counter

import polars as pl
from textkey import key

W = "data/collusion_wiki/"
SIG = re.compile(r"--\s*([A-Za-z][\w$()+%.-]{2,})\s*$")


def line_authors(rows):
    """remove row id -> label of the latest earlier add on the same page holding its lines (majority over lines)."""
    adds, out = {}, {}
    for r in rows:
        lines = [x.strip() for x in (r["text"] or "").splitlines() if x.strip()]
        if r["kind"] == "add":
            adds.setdefault(r["page"], []).append((r["rev"], r["label"], set(lines)))
        elif r["kind"] == "remove" and lines:
            votes = Counter()
            for line in lines:
                for rev, label, held in reversed(adds.get(r["page"], [])):
                    if rev != r["rev"] and line in held:
                        votes[label] += 1
                        break
            if votes:
                out[r["id"]] = votes.most_common(1)[0][0]
    return out


def signature(text):
    found = [
        m.group(1) for line in text.splitlines() if (m := SIG.search(line.strip()))
    ]
    return found[-1] if found else None


def jsonl(name):
    with gzip.open(W + name, "rt") as fh:
        return [json.loads(line) for line in fh]


pfam = {p["page_key"]: p.get("page_family") for p in jsonl("pages.jsonl.gz")}
revs = jsonl("revisions.jsonl.gz")
lines = {r["rev_id"]: (r.get("body") or "").split("\n") for r in revs}

rows = []
for r in revs:
    new, old = lines[r["rev_id"]], lines.get(r.get("diff_base"), [])
    base = {
        "page": r["page_key"],
        "wiki": r["wiki"],
        "page_family": pfam.get(r["page_key"]),
        "label": r.get("label"),
        "ip16": r.get("ip16"),
        "time": r["time"],
        "rev": r["rev_id"],
        "rev_seq": r["seq"],
        "request_action": r.get("request_action"),
        "param_family": None,
    }
    for i, h in enumerate(r.get("hunks") or []):
        parts = []
        if h["op"] in ("insert", "replace"):
            parts.append(("add", new[h["b0"] : h["b1"]]))
        if h["op"] in ("delete", "replace"):
            parts.append(("remove", old[h["a0"] : h["a1"]]))
        for kind, chunk in parts:
            text = "\n".join(chunk).strip()
            if text:
                rows.append(dict(base, kind=kind, hunk=i, op=h["op"], text=text))

for e in jsonl("events.jsonl.gz"):
    if e["event_type"] == "save":
        continue
    rows.append(
        {
            "page": e.get("page_key"),
            "wiki": e.get("wiki"),
            "page_family": pfam.get(e.get("page_key")),
            "label": e.get("actor_label"),
            "ip16": e.get("ip16"),
            "time": e["time"],
            "rev": e["event_id"],
            "rev_seq": None,
            "request_action": e.get("request_action"),
            "param_family": e.get("param_family"),
            "kind": e["event_type"],
            "hunk": 0,
            "op": None,
            "text": e.get("change_summary") or "",
        }
    )

df = (
    pl.DataFrame(rows, infer_schema_length=None)
    .with_columns(pl.col("time").str.to_datetime(time_zone="UTC"))
    .sort("time", "page", "rev_seq", "hunk", "kind", nulls_last=True)
    .with_row_index("seq")
    .with_columns(
        (
            pl.col("rev") + "#" + pl.col("hunk").cast(pl.Utf8) + ":" + pl.col("kind")
        ).alias("id"),
        pl.col("text").map_elements(key, return_dtype=pl.Utf8).alias("text_key"),
    )
)
msg = pl.col("kind").is_in(["add", "remove"])
df = (
    df.with_columns(
        pl.when((pl.col("kind") == "add") & pl.col("text_key").is_not_null())
        .then(
            pl.col("seq")
            == pl.col("seq").filter(pl.col("kind") == "add").min().over("text_key")
        )
        .alias("first_of_text")
    )
    .with_columns(pl.when(msg).then(pl.col("text_key")).alias("text_key"))
    .sort("seq")
    .with_columns(
        # adds only: new = first time anywhere; readd = already added on this page; copy = seen only on other pages
        pl.when(pl.col("first_of_text").is_null())
        .then(None)
        .when(pl.col("first_of_text"))
        .then(pl.lit("new"))
        .when((pl.col("kind") == "add").cum_sum().over("page", "text_key") > 1)
        .then(pl.lit("readd"))
        .otherwise(pl.lit("copy"))
        .alias("add_type")
    )
)
authors = line_authors(
    df.sort("seq")
    .select("id", "page", "rev", "kind", "label", "text")
    .iter_rows(named=True)
)
df = df.with_columns(
    pl.when(msg)
    .then(pl.col("text").map_elements(signature, return_dtype=pl.Utf8))
    .alias("signature"),
    pl.col("id").replace_strict(authors, default=None).alias("author_label"),
).with_columns(
    pl.when(pl.col("kind") == "remove")
    .then(pl.col("label") != pl.col("author_label"))
    .alias("by_other")
)
assert df["id"].is_unique().all()
df.write_parquet("data/wiki_msgs_rows.parquet")
print(
    df.height,
    "rows |",
    df.group_by("kind").len().sort("len", descending=True).to_dicts(),
)
print(
    "revisions without a change row:",
    len({r["rev_id"] for r in revs} - set(df.filter(msg)["rev"].to_list())),
)
