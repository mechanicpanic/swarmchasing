"""C30 base tables: signers, message-level removal events with latest-earlier adder, saves of each label.
Writes c30/base_*.parquet. Run from repo root with .venv python."""
import gzip, json, re
import polars as pl

S = __import__("os").environ.get("OUT", "results/c30/")
d = pl.read_parquet("data/wiki_msgs.parquet")

# --- signatures (patterns adapted from PR #7 runs/wiki-june18/signatures_sig.py), per line of added text
P_EOL = re.compile(r'(?:^|\s)--\s?([A-Za-z][\w.\-]{1,60}?)[.?!*,;]*\s*(?:\$\(.*|\[M\d+\]|\\n)?\s*$')
P_HDR = re.compile(r'(?:^|\s)--\s([A-Za-z][\w\-]{2,60}):\s')
P_TILDE = re.compile(r'(?:^|\s)~{1,4}\s?([A-Z][\w\-]{2,60})\s*$')
P_SIGNED = re.compile(r'(?i)\b(?:signed(?:\s+by)?|signature)\s*[:,]?\s+([A-Za-z][\w\-]{2,60})')
P_DASHU = re.compile(r'[—–]\s?([A-Za-z][\w\-]{2,60})\s*$')
FORMS = [("eol", P_EOL), ("header", P_HDR), ("tilde", P_TILDE), ("signed", P_SIGNED), ("emdash", P_DASHU)]
STOP = {"data", "format", "header", "request", "get", "url", "output", "compressed", "insecure", "location", "silent",
        "help", "version", "verbose", "data-urlencode", "max-time", "user-agent", "include", "head", "fail", "retry"}


def sig(text):
    for line in text.split("\n"):
        for part in line.split("\\n"):
            for form, p in FORMS:
                for m in p.finditer(part):
                    name = m.group(1).rstrip(".-")
                    if name.lower() in STOP or len(name) < 3:
                        continue
                    return f"{form}:{name}"
    return None


adds = d.filter(pl.col("kind") == "add")
adds = adds.with_columns(pl.col("text").map_elements(sig, return_dtype=pl.Utf8).alias("sig"))
adds.select("id", "time", "page", "label", "add_type", "sig", "text").write_parquet(S + "base_adds.parquet")
signed_new = adds.filter(pl.col("sig").is_not_null() & (pl.col("add_type") == "new") & pl.col("label").is_not_null())
signers = set(signed_new["label"].unique().to_list())
labels = set(d.filter(pl.col("kind").is_in(["add", "remove"]) & pl.col("label").is_not_null())["label"].unique().to_list())
print("labels with a save", len(labels), "| signers", len(signers & labels), "| non-signers", len(labels - signers))
print("signed new add rows", signed_new.height, "| any signed add rows", adds.filter(pl.col("sig").is_not_null()).height)
pl.DataFrame({"label": sorted(labels), "signer": [l in signers for l in sorted(labels)]}).write_parquet(S + "base_groups.parquet")

# --- whole-page removals: removed text == the whole (non-empty) base body
revs = [json.loads(l) for l in gzip.open("data/collusion_wiki/revisions.jsonl.gz", "rt")]
body = {r["rev_id"]: r.get("body") or "" for r in revs}
base_of = {r["rev_id"]: r.get("diff_base") for r in revs}
summ = {r["rev_id"]: r.get("change_summary") for r in revs}


def nl(s):
    return "\n".join(x.strip() for x in s.split("\n") if x.strip())


def whole(rev, text):
    b = base_of.get(rev)
    return b is not None and b in body and nl(body[b]) == nl(text)


def whole_new(rev, text):
    return rev in body and nl(body[rev]) == nl(text)


msg = d.filter(pl.col("kind").is_in(["add", "remove"]) & pl.col("text_key").is_not_null()).sort("seq")
# latest earlier adder of (page, text_key) at each remove
rows = msg.select("seq", "id", "time", "page", "label", "rev", "kind", "op", "text_key", "text")
last_add = None
out = []
latest = {}
for r in rows.iter_rows(named=True):
    k = (r["page"], r["text_key"])
    if r["kind"] == "add":
        latest[k] = r["label"]
    else:
        out.append(dict(r, A=latest.get(k), whole_base=whole(r["rev"], r["text"])))
rem = pl.DataFrame(out, infer_schema_length=None)
# does the same rev also add a whole new page (replace -> replace)?
rem = rem.with_columns(pl.Series("summary", [summ.get(x) for x in rem["rev"]]))
print("remove rows with key", rem.height, "| no earlier adder", rem["A"].is_null().sum(),
      "| whole-base removes", rem["whole_base"].sum())
rem.write_parquet(S + "base_removes.parquet")

# saves: one row per (rev) with label/page/time, its added keys, and its added text
sv = (d.filter(pl.col("kind") == "add").group_by("rev")
      .agg(pl.col("time").first(), pl.col("page").first(), pl.col("label").first(),
           pl.col("text_key").drop_nulls().alias("keys"), pl.col("text").str.join("\n").alias("added")))
# saves with only removes (no add row) also are saves: include them with empty adds
rv = d.filter(pl.col("kind") == "remove").group_by("rev").agg(pl.col("time").first(), pl.col("page").first(), pl.col("label").first())
rv = rv.join(sv.select("rev"), on="rev", how="anti").with_columns(pl.lit([]).cast(pl.List(pl.Utf8)).alias("keys"), pl.lit("").alias("added"))
saves = pl.concat([sv, rv.select(sv.columns)]).with_columns(pl.Series("summary", [None]*0, dtype=pl.Utf8) if False else pl.lit(None).alias("_"))
saves = saves.drop("_").with_columns(pl.col("rev").map_elements(lambda x: summ.get(x), return_dtype=pl.Utf8).alias("summary"))
print("saves", saves.height)
saves.write_parquet(S + "base_saves.parquet")
