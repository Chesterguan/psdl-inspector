"""Write the semantic catalog to CSV artifacts (Stage 03 outputs).

  column_catalog.csv           one row per distinct (normalized) column
  schema_semantic_catalog.csv  one row per distinct schema signature
"""

from __future__ import annotations

import csv
import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Dict, Union

from psdl_observatory.catalog import CatalogResult
from psdl_observatory.models import ScanResult
from psdl_observatory.roles import ALL_ROLES


def write_column_catalog_csv(catalog: CatalogResult, path: Union[str, Path]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["column", "role", "file_count", "schema_count", "example_path"])
        for c in catalog.columns:
            w.writerow([c.normalized, c.role, c.file_count, c.schema_count, c.example_path])
    return path


def write_schema_semantic_catalog_csv(catalog: CatalogResult, path: Union[str, Path]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    role_cols = [f"n_{r}" for r in ALL_ROLES]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["schema_signature", "num_files", "num_columns", "table_kind",
                    "roles_present", "columns"] + role_cols)
        for s in catalog.schemas:
            w.writerow([
                s.schema_signature, s.num_files, s.num_columns, s.table_kind,
                "|".join(s.roles_present), "|".join(s.columns),
            ] + [s.role_counts.get(r, 0) for r in ALL_ROLES])
    return path


def write_catalog_all(catalog: CatalogResult, out_dir: Union[str, Path]) -> Dict[str, Path]:
    out_dir = Path(out_dir)
    return {
        "columns": write_column_catalog_csv(catalog, out_dir / "column_catalog.csv"),
        "schemas": write_schema_semantic_catalog_csv(catalog, out_dir / "schema_semantic_catalog.csv"),
    }


def _scanner_version() -> str:
    try:
        return version("psdl-observatory")
    except PackageNotFoundError:
        return "unknown"


def write_catalog_json(
    catalog: CatalogResult,
    scan: ScanResult,
    path: Union[str, Path],
    scanned_at: str,
) -> Path:
    """Serialize the catalog + scan provenance to catalog.json (contract v1.1).

    `scanned_at` is passed in (ISO-8601) so callers control the timestamp and the
    output is deterministic for tests; the CLI stamps the real wall-clock time.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "catalog_version": "1.1",
        "provenance": {
            "scanned_at": scanned_at,
            "root": scan.root,
            "file_count": scan.total_files,
            "schema_count": scan.distinct_schema_count,
            "scanner_version": _scanner_version(),
        },
        "schemas": [
            {
                "schema_signature": s.schema_signature,
                "table_kind": s.table_kind,
                "num_files": s.num_files,
                "num_rows": s.num_rows,
                "roles_present": s.roles_present,
                "role_counts": s.role_counts,
                "columns": s.columns,
                "example_path": s.example_path,
            }
            for s in catalog.schemas
        ],
        "columns": [
            {
                "normalized": c.normalized,
                "role": c.role,
                "file_count": c.file_count,
                "schema_count": c.schema_count,
                "example_path": c.example_path,
            }
            for c in catalog.columns
        ],
    }
    path.write_text(json.dumps(payload, indent=2))
    return path
