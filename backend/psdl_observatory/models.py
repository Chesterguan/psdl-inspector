"""Data models for the Observatory inventory scan."""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class ParquetFileInfo:
    """Footer-derived metadata for a single parquet file. No row data."""

    relative_path: str
    size_bytes: int
    num_rows: int
    num_row_groups: int
    columns: Tuple[str, ...]
    schema_signature: str

    @property
    def num_columns(self) -> int:
        return len(self.columns)

    @property
    def filename(self) -> str:
        return os.path.basename(self.relative_path)


@dataclass
class ScanResult:
    """Aggregate result of scanning a parquet lake."""

    root: str
    files: List[ParquetFileInfo]
    errors: List[Tuple[str, str]] = field(default_factory=list)  # (relative_path, message)

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_rows(self) -> int:
        return sum(f.num_rows for f in self.files)

    @property
    def total_size_bytes(self) -> int:
        return sum(f.size_bytes for f in self.files)

    @property
    def distinct_schema_count(self) -> int:
        return len({f.schema_signature for f in self.files})

    def duplicate_filenames(self) -> Dict[str, List[str]]:
        """Basenames that occur at more than one relative path → sorted paths.

        Assumes each ParquetFileInfo.relative_path is unique within
        self.files (the scanner guarantees this — os.walk yields each path once).
        """
        by_name: Dict[str, List[str]] = defaultdict(list)
        for f in self.files:
            by_name[f.filename].append(f.relative_path)
        return {
            name: sorted(paths)
            for name, paths in by_name.items()
            if len(paths) > 1
        }
