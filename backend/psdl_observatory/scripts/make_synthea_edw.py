#!/usr/bin/env python3
"""Build a synthetic EDW parquet lake from Synthea sample CSVs.

Synthea (synthetichealth/synthea) produces fully synthetic patient records --
no PHI, no credentialing required (contrast with MIMIC). We download the
published sample CSV dataset and convert each table (patients, encounters,
conditions, medications, observations, procedures, ...) to parquet, sharded,
so the Observatory scanner has a realistic "new EDW" to inventory.

Usage:
    python scripts/make_synthea_edw.py --out /tmp/synthea_edw [--shards 3]
"""
from __future__ import annotations

import argparse
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

# Synthea public sample CSV dataset (synthetic, ~100 patients, MIT-licensed).
SYNTHEA_SAMPLE_URL = (
    "https://synthetichealth.github.io/synthea-sample-data/downloads/"
    "synthea_sample_data_csv_apr2020.zip"
)


def build(out_dir: Path, shards: int = 3) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"downloading Synthea sample CSVs from {SYNTHEA_SAMPLE_URL} ...")
    with urllib.request.urlopen(SYNTHEA_SAMPLE_URL) as resp:  # noqa: S310 (trusted URL)
        data = resp.read()
    zf = zipfile.ZipFile(io.BytesIO(data))
    csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    print(f"found {len(csv_names)} CSV tables")
    for name in csv_names:
        table_name = Path(name).stem.lower()
        with zf.open(name) as f:
            tbl = pacsv.read_csv(f)
        # shard each table into N parquet parts under a per-table dir
        n = tbl.num_rows
        if n == 0:
            continue
        per = max(1, (n + shards - 1) // shards)
        tdir = out_dir / table_name
        tdir.mkdir(parents=True, exist_ok=True)
        for i in range(0, n, per):
            part = tbl.slice(i, per)
            pq.write_table(part, tdir / f"{table_name}-{i // per}.parquet")
        print(f"  {table_name}: {n} rows -> {tdir}")
    print(f"done: synthetic EDW parquet lake at {out_dir}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--shards", type=int, default=3)
    a = ap.parse_args()
    build(Path(a.out), a.shards)
    return 0


if __name__ == "__main__":
    sys.exit(main())
