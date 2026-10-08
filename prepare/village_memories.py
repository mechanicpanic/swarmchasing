"""AI Village agent memories → one Parquet of versions, plus a small index.

Each row of `agent_memories.jsonl.gz` is the whole memory file of one agent at
one rewrite (median ~18k chars, ~6.8 GB of text in all), stored in id (uuid)
order. Output, sorted by (agent, created_at):

- data/village_memories.parquet: agent_id, agent, version (0..n-1 per agent),
  created_at (UTC), length, content — small row groups, so reading one
  version reads one group.
- data/village_memories_index.parquet: the same rows without content, plus
  `row` (position in the big file) and `header` (first non-empty line).

The content never sits in memory whole: pass 1 reads only the metadata and
fixes the final order; pass 2 streams the export again and spills each row
into a bucket (a range of final positions) on disk; pass 3 sorts one bucket
at a time and appends it to the output.
"""

from __future__ import annotations

import gzip
import json
import shutil
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

SRC = Path("data/village/agent_memories.jsonl.gz")
AGENTS = Path("data/village/agents.jsonl.gz")
DST = Path("data/village_memories.parquet")
INDEX = Path("data/village_memories_index.parquet")
TMP = Path("data/.village_memories_tmp")
ROW_GROUP = 64  # rows per row group (~1-2 MB of text)
BUCKET_CHARS = 50_000_000  # text per bucket held in memory in pass 3
FLUSH_CHARS = 40_000_000  # text buffered in pass 2 before all buffers are written


def rows():
    with gzip.open(SRC, "rt", encoding="utf-8") as fh:
        for line in fh:
            yield json.loads(line)


def header(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:160]
    return ""


def index() -> pl.DataFrame:
    """Pass 1: metadata only, in final order, with each row's bucket."""
    meta = [
        (
            r["id"],
            r["agent_id"],
            r["created_at"],
            len(c := r["content"] or ""),
            header(c),
        )
        for r in rows()
    ]
    cols = ["id", "agent_id", "created_at", "length", "header"]
    df = pl.DataFrame(meta, schema=cols, orient="row")
    with gzip.open(AGENTS, "rt", encoding="utf-8") as fh:
        names = pl.DataFrame([json.loads(x) for x in fh]).select(
            pl.col("id").alias("agent_id"), pl.col("name").alias("agent")
        )
    ts = pl.col("created_at").str.to_datetime("%Y-%m-%d %H:%M:%S%.f", time_zone="UTC")
    return (
        df.join(names, on="agent_id", how="left")
        .with_columns(pl.col("agent").fill_null(pl.col("agent_id")), ts)
        .sort("agent", "created_at", "id")
        .with_columns(
            version=pl.int_range(pl.len()).over("agent").cast(pl.Int32),
            row=pl.int_range(pl.len()).cast(pl.Int64),
        )
        .with_columns(
            bucket=(pl.col("length").cum_sum() // BUCKET_CHARS).cast(pl.Int32)
        )
    )


def spill(idx: pl.DataFrame) -> None:
    """Pass 2: each row's (row, content) into its bucket file."""
    where = dict(zip(idx["id"], zip(idx["row"], idx["bucket"])))
    schema = pa.schema([("row", pa.int64()), ("content", pa.large_string())])
    writers: dict[int, pq.ParquetWriter] = {}
    bufs: dict[int, list] = {}

    def flush(b: int) -> None:
        if b not in writers:
            writers[b] = pq.ParquetWriter(TMP / f"{b:04d}.parquet", schema)
        rs, cs = zip(*bufs.pop(b))
        writers[b].write_table(pa.table([list(rs), list(cs)], schema=schema))

    held = 0
    for r in rows():
        row, b = where[r["id"]]
        c = r["content"] or ""
        bufs.setdefault(b, []).append((row, c))
        held += len(c)
        if held >= FLUSH_CHARS:
            for b in list(bufs):
                flush(b)
            held = 0
    for b in list(bufs):
        flush(b)
    for w in writers.values():
        w.close()


def assemble(idx: pl.DataFrame) -> None:
    """Pass 3: one bucket at a time, sorted, appended to the output."""
    meta = idx.select("row", "agent_id", "agent", "version", "created_at", "length")
    writer = None
    for f in sorted(TMP.glob("*.parquet")):
        part = (
            pl.read_parquet(f)
            .join(meta, on="row")
            .sort("row")
            .select("agent_id", "agent", "version", "created_at", "length", "content")
        )
        table = part.to_arrow()
        if writer is None:
            writer = pq.ParquetWriter(DST, table.schema, compression="zstd")
        writer.write_table(table, row_group_size=ROW_GROUP)
        del part, table
    writer.close()


def main() -> None:
    idx = index()
    shutil.rmtree(TMP, ignore_errors=True)
    TMP.mkdir(parents=True)
    spill(idx)
    assemble(idx)
    shutil.rmtree(TMP)
    idx.select(
        "agent_id", "agent", "version", "created_at", "length", "row", "header", "id"
    ).write_parquet(INDEX)
    n = pq.ParquetFile(DST).metadata
    print(f"{DST}: {n.num_rows} rows, {n.num_row_groups} row groups; {INDEX}")


if __name__ == "__main__":
    main()
