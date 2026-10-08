"""Reader for AI Village agents' memory files: every rewrite of each agent's
memory, the diff between any two, where a phrase appears and disappears, and
what the agent said and thought just before a rewrite.

Reads data/village_memories{,_index}.parquet (`make village-memories`) and
data/village.parquet (context), all local. Run: make memory [MEMORY_PORT=8970].
"""

from __future__ import annotations

import argparse
import bisect
import difflib
import gzip
import json
import os
import re
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import polars as pl
import pyarrow.compute as pc
import pyarrow.parquet as pq
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("MEMORY_DATA", HERE.parent.parent / "data"))
CTX = 2  # unchanged lines shown around a change
CONTEXT_KINDS = ["AGENT_TALK", "THOUGHT", "CONSOLIDATE"]

INDEX = pl.read_parquet(DATA / "village_memories_index.parquet").sort("row")
FILE = pq.ParquetFile(DATA / "village_memories.parquet")
STARTS = [0]  # first row of each row group
for i in range(FILE.metadata.num_row_groups):
    STARTS.append(STARTS[-1] + FILE.metadata.row_group(i).num_rows)
with gzip.open(DATA / "village" / "agents.jsonl.gz", "rt", encoding="utf-8") as fh:
    PROFILES = {a["id"]: a for a in map(json.loads, fh)}

app = FastAPI(title="Village memory reader")


@lru_cache(maxsize=32)
def group(i: int) -> list[str]:
    return FILE.read_row_group(i, columns=["content"]).column(0).to_pylist()


def text(row: int) -> str:
    i = bisect.bisect_right(STARTS, row) - 1
    return group(i)[row - STARTS[i]] or ""


def versions(agent: str) -> pl.DataFrame:
    df = INDEX.filter((pl.col("agent") == agent) | (pl.col("agent_id") == agent))
    if df.is_empty():
        raise HTTPException(404, f"no memory versions for agent {agent!r}")
    return df


def meta(df: pl.DataFrame, v: int) -> dict:
    if not 0 <= v < df.height:
        raise HTTPException(404, f"version {v} out of range 0..{df.height - 1}")
    r = df.row(v, named=True)
    return {k: r[k] for k in ("version", "row", "length", "header")} | {
        "created_at": r["created_at"].isoformat()
    }


@app.get("/")
def page() -> FileResponse:
    return FileResponse(HERE / "memory.html")


@app.get("/api/agents")
def agents() -> list[dict]:
    g = INDEX.group_by("agent_id", "agent").agg(
        versions=pl.len(),
        first=pl.col("created_at").min(),
        last=pl.col("created_at").max(),
    )
    out = []
    for r in g.sort("agent").iter_rows(named=True):
        p = PROFILES.get(r["agent_id"], {})
        out.append(
            r
            | {"first": r["first"].isoformat(), "last": r["last"].isoformat()}
            | {"emoji": p.get("emoji", ""), "model_string": p.get("model_string", "")}
        )
    return out


@app.get("/api/versions")
def agent_versions(agent: str) -> dict:
    """Columnar, so the largest agent (~34k versions) stays a small response."""
    df = versions(agent)
    return {
        "agent": df["agent"][0],
        "version": df["version"].to_list(),
        "created_at": [t.isoformat() for t in df["created_at"]],
        "length": df["length"].to_list(),
        "header": df["header"].str.slice(0, 100).to_list(),
    }


@app.get("/api/version")
def version(agent: str, v: int) -> dict:
    m = meta(versions(agent), v)
    return m | {"content": text(m["row"])}


def words(a: str, b: str) -> tuple[list, list] | None:
    """Word-level marks inside a replaced line pair: [[op, text], ...] each side."""
    ta, tb = re.split(r"(\s+)", a), re.split(r"(\s+)", b)
    sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
    if sm.ratio() < 0.4:
        return None
    left, right = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if i2 > i1:
            left.append(["=" if op == "equal" else "-", "".join(ta[i1:i2])])
        if j2 > j1:
            right.append(["=" if op == "equal" else "+", "".join(tb[j1:j2])])
    return left, right


def blocks(a: list[str], b: list[str]) -> list[dict]:
    out = []
    sm = difflib.SequenceMatcher(None, a, b, autojunk=len(a) + len(b) > 20000)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        blk = {"op": op, "a": i1, "b": j1}
        if op == "equal":
            same = a[i1:i2]
            if len(same) > 2 * CTX + 1:
                blk |= {
                    "head": same[:CTX],
                    "hidden": same[CTX:-CTX],
                    "tail": same[-CTX:],
                }
            else:
                blk |= {"head": same, "hidden": [], "tail": []}
        else:
            blk |= {"del": a[i1:i2], "ins": b[j1:j2]}
            if op == "replace" and i2 - i1 == j2 - j1 and i2 - i1 <= 50:
                pairs = [words(x, y) for x, y in zip(a[i1:i2], b[j1:j2])]
                if all(
                    p and len(x) + len(y) < 4000
                    for p, x, y in zip(pairs, a[i1:i2], b[j1:j2])
                ):
                    blk["words"] = pairs
        out.append(blk)
    return out


@app.get("/api/diff")
def diff(agent: str, a: int, b: int | None = None) -> dict:
    df = versions(agent)
    b = a + 1 if b is None else b
    ma, mb = meta(df, a), meta(df, b)
    la, lb = text(ma["row"]).splitlines(), text(mb["row"]).splitlines()
    bl = blocks(la, lb)
    added = sum(len(x.get("ins", [])) for x in bl)
    removed = sum(len(x.get("del", [])) for x in bl)
    return {"a": ma, "b": mb, "added": added, "removed": removed, "blocks": bl}


@lru_cache(maxsize=64)
def search_cached(agent: str, q: str) -> dict:
    df = versions(agent)
    r0, r1 = df["row"][0], df["row"][-1]
    hits: list[bool] = []
    snippets: dict[int, str] = {}
    ql = q.lower()
    for i in range(
        bisect.bisect_right(STARTS, r0) - 1, bisect.bisect_right(STARTS, r1)
    ):
        col = FILE.read_row_group(i, columns=["content"]).column(0)
        lo, hi = max(r0 - STARTS[i], 0), min(r1 - STARTS[i] + 1, len(col))
        part = col.slice(lo, hi - lo)
        found = (
            pc.match_substring(part, q, ignore_case=True).fill_null(False).to_pylist()
        )
        for k, f in enumerate(found):
            v = len(hits)
            if f and (not hits or not hits[-1]):
                s = part[k].as_py()
                j = s.lower().find(ql)
                snippets[v] = s[max(j - 100, 0) : j + len(q) + 140]
            hits.append(f)
    out, seen, prev = [], False, False
    for v, f in enumerate(hits):
        if f != prev:
            ev = ("reappears" if seen else "appears") if f else "disappears"
            out.append({"version": v, "event": ev, "snippet": snippets.get(v, "")})
            seen |= f
        prev = f
    times = df["created_at"]
    for t in out:
        t["created_at"] = times[t["version"]].isoformat()
    return {"q": q, "versions": len(hits), "with": sum(hits), "transitions": out}


@app.get("/api/search")
def search(agent: str, q: str) -> dict:
    if not q.strip():
        raise HTTPException(400, "empty q")
    return search_cached(versions(agent)["agent"][0], q)


@app.get("/api/context")
def context(agent: str, t: str, minutes: int = 30) -> list[dict]:
    aid = versions(agent)["agent_id"][0]
    end = datetime.fromisoformat(t)
    end = end if end.tzinfo else end.replace(tzinfo=UTC)
    df = (
        pl.scan_parquet(DATA / "village.parquet")
        .filter(
            (pl.col("agent_id") == aid)
            & pl.col("time").is_between(end - timedelta(minutes=minutes), end)
            & pl.col("kind").is_in(CONTEXT_KINDS)
        )
        .select("time", "kind", "room", "text")
        .sort("time")
        .tail(300)
        .collect()
    )
    return [r | {"time": r["time"].isoformat()} for r in df.iter_rows(named=True)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8970)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
