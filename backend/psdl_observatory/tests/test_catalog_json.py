"""Tests for num_rows aggregation, the JSON writer, and the --json CLI."""

import json

from psdl_observatory import scan_inventory
from psdl_observatory.catalog import build_catalog


def test_build_catalog_populates_num_rows(parquet_lake):
    scan = scan_inventory(parquet_lake)
    cat = build_catalog(scan)
    # Every schema profile carries a row total.
    assert all(isinstance(s.num_rows, int) for s in cat.schemas)
    # Each file belongs to exactly one schema signature, so schema row totals
    # sum to the scan's total rows.
    assert sum(s.num_rows for s in cat.schemas) == scan.total_rows


def test_write_catalog_json_shape(parquet_lake, tmp_path):
    from psdl_observatory.catalog_writers import write_catalog_json

    scan = scan_inventory(parquet_lake)
    cat = build_catalog(scan)
    out = tmp_path / "catalog.json"
    from pathlib import Path
    result = write_catalog_json(cat, scan, out, scanned_at="2026-06-03T10:00:00+00:00")
    assert isinstance(result, Path)

    data = json.loads(out.read_text())
    assert data["catalog_version"] == "1.1"
    prov = data["provenance"]
    assert prov["scanned_at"] == "2026-06-03T10:00:00+00:00"
    assert prov["root"] == str(parquet_lake)
    assert prov["file_count"] == scan.total_files
    assert prov["schema_count"] == scan.distinct_schema_count
    assert prov["scan_error_count"] == len(scan.errors)
    assert isinstance(prov["scanner_version"], str)
    # schemas carry num_rows; columns carry role
    assert all("num_rows" in s for s in data["schemas"])
    assert all("role" in c for c in data["columns"])
    assert len(data["schemas"]) == scan.distinct_schema_count
    assert len(data["columns"]) == len(cat.columns)


def test_cli_catalog_json_emits_file(parquet_lake, tmp_path):
    from psdl_observatory.cli import main

    rc = main(["catalog", str(parquet_lake), "--out", str(tmp_path), "--json"])
    assert rc == 0
    out = tmp_path / "catalog.json"
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["catalog_version"] == "1.1"
    assert data["provenance"]["scanned_at"]  # non-empty timestamp
