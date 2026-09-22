"""Anything → an ordered event stream PrismQL can load.

Usage:
    uv run python ingest/village.py <table.parquet|.csv|.jsonl> data/<out>.jsonl \
        --id <id column> --time <timestamp column> [--sort <column>] [--keep col1,col2,...]

Rows come out in the order PrismQL will treat as the stream (load order =
position): pass --sort to order by a column first (usually the time column).
Keeps `id` and `time` under those names plus the --keep columns; everything
else is dropped so the frame stays small. The Village export (chat_messages,
events, sessions, turns, memories) is gated — fill the column names in once it
is here; nothing about its schema is assumed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--id", required=True)
    ap.add_argument("--time", required=True)
    ap.add_argument("--sort", default=None, help="column to order the stream by")
    ap.add_argument("--keep", default="", help="comma-separated extra columns")
    a = ap.parse_args()

    src = Path(a.src)
    if src.suffix == ".parquet":
        df = pl.read_parquet(src)
    elif src.suffix == ".csv":
        df = pl.read_csv(src)
    else:
        df = pl.read_ndjson(src)
    keep = [c for c in a.keep.split(",") if c]
    if a.sort:
        df = df.sort(a.sort)
    out = df.select(
        pl.col(a.id).cast(pl.Utf8).alias("id"),
        pl.col(a.time).alias("time"),
        *[pl.col(c) for c in keep],
    )
    out.write_ndjson(a.dst)
    print(f"{len(out)} rows → {a.dst}; columns: {out.columns}")


if __name__ == "__main__":
    main()
