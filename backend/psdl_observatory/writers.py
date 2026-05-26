"""Write the inventory scan to CSV/TXT artifacts.

Outputs (per the methodology Stage 01):
  parquet_inventory.csv   one row per parquet file
  duplicate_filenames.csv basenames occurring at >1 path
  scan_summary.txt        human-readable totals
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Union

from psdl_observatory.models import ScanResult


def write_inventory_csv(result: ScanResult, path: Union[str, Path]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["relative_path", "filename", "size_bytes", "num_rows",
                    "num_row_groups", "num_columns", "schema_signature", "columns"])
        for fi in result.files:
            w.writerow([fi.relative_path, fi.filename, fi.size_bytes, fi.num_rows,
                        fi.num_row_groups, fi.num_columns, fi.schema_signature,
                        "|".join(fi.columns)])
    return path


def write_duplicates_csv(result: ScanResult, path: Union[str, Path]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["filename", "count", "paths"])
        for name, paths in sorted(result.duplicate_filenames().items()):
            w.writerow([name, len(paths), "|".join(paths)])
    return path


def write_summary_txt(result: ScanResult, path: Union[str, Path]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "PSDL Observatory — Inventory Scan Summary",
        "=" * 44,
        f"Root: {result.root}",
        f"Total files: {result.total_files}",
        f"Total rows: {result.total_rows}",
        f"Total size (bytes): {result.total_size_bytes}",
        f"Distinct schemas: {result.distinct_schema_count}",
        f"Duplicate filenames: {len(result.duplicate_filenames())}",
        f"Errors: {len(result.errors)}",
    ]
    if result.errors:
        lines.append("")
        lines.append("Errors:")
        for rel, msg in result.errors:
            lines.append(f"  {rel}: {msg}")
    path.write_text("\n".join(lines) + "\n")
    return path


def write_all(result: ScanResult, out_dir: Union[str, Path]) -> Dict[str, Path]:
    out_dir = Path(out_dir)
    return {
        "inventory": write_inventory_csv(result, out_dir / "parquet_inventory.csv"),
        "duplicates": write_duplicates_csv(result, out_dir / "duplicate_filenames.csv"),
        "summary": write_summary_txt(result, out_dir / "scan_summary.txt"),
    }
