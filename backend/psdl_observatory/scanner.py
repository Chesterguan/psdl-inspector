"""Parquet-footer inventory scanner.

Reads ONLY parquet footers (metadata + schema) — never row data, never PHI.
Parallelized with ThreadPoolExecutor (footer reads are I/O-bound).
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple, Union

import pyarrow.parquet as pq

from psdl_observatory.models import ParquetFileInfo, ScanResult
from psdl_observatory.schema_sig import schema_signature


def _find_parquet_files(root: Path) -> List[Path]:
    out: List[Path] = []
    # os.walk does not follow directory symlinks by default; symlinked dataset mounts are
    # intentionally not traversed in O1 (avoids cycles/double-counting).
    # followlinks support can be added later if needed.
    for dirpath, _dirs, filenames in os.walk(root):
        for name in filenames:
            if name.endswith(".parquet"):
                out.append(Path(dirpath) / name)
    return out


def read_parquet_footer(path: Union[str, Path], root: Union[str, Path]) -> ParquetFileInfo:
    """Read one parquet file's footer (no rows) into a ParquetFileInfo."""
    path = Path(path)
    root = Path(root)
    size_bytes = path.stat().st_size     # stat first — fail-fast before any footer read
    md = pq.read_metadata(path)          # footer only
    # Second footer read: PyArrow has no way to derive the Arrow schema from an
    # already-parsed FileMetaData, so this is required (don't "optimize" it away).
    schema = pq.read_schema(path)        # footer only
    columns = tuple(schema.names)
    types = [str(schema.field(n).type) for n in schema.names]
    rel = str(path.relative_to(root))
    return ParquetFileInfo(
        relative_path=rel,
        size_bytes=size_bytes,
        num_rows=md.num_rows,
        num_row_groups=md.num_row_groups,
        columns=columns,
        schema_signature=schema_signature(list(columns), types),
    )


def scan_inventory(
    root: Union[str, Path],
    workers: int = 8,
) -> ScanResult:
    """Walk `root` for *.parquet, read footers in parallel, return a ScanResult.

    Footer-read failures (corrupt / non-parquet files) are collected in
    ScanResult.errors rather than aborting the scan.
    """
    root = Path(root)
    files = _find_parquet_files(root)
    infos: List[ParquetFileInfo] = []
    errors: List[Tuple[str, str]] = []

    if not files:
        return ScanResult(root=str(root), files=infos, errors=errors)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(read_parquet_footer, p, root): p for p in files}
        for fut in as_completed(futures):
            p = futures[fut]
            try:
                infos.append(fut.result())
            except Exception as e:  # corrupt/unreadable footer
                rel = str(p.relative_to(root))
                errors.append((rel, f"{type(e).__name__}: {e}"))

    infos.sort(key=lambda i: i.relative_path)
    errors.sort()
    return ScanResult(root=str(root), files=infos, errors=errors)
