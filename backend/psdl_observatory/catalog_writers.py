"""Write the semantic catalog to CSV artifacts (Stage 03 outputs).

  column_catalog.csv           one row per distinct (normalized) column
  schema_semantic_catalog.csv  one row per distinct schema signature
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Union

from psdl_observatory.catalog import CatalogResult
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
                s.schema_signature, s.num_files, len(s.columns), s.table_kind,
                "|".join(s.roles_present), "|".join(s.columns),
            ] + [s.role_counts.get(r, 0) for r in ALL_ROLES])
    return path


def write_catalog_all(catalog: CatalogResult, out_dir: Union[str, Path]) -> Dict[str, Path]:
    out_dir = Path(out_dir)
    return {
        "columns": write_column_catalog_csv(catalog, out_dir / "column_catalog.csv"),
        "schemas": write_schema_semantic_catalog_csv(catalog, out_dir / "schema_semantic_catalog.csv"),
    }
