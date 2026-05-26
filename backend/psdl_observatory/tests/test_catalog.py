"""Tests for build_catalog over a ScanResult."""

from psdl_observatory import scan_inventory
from psdl_observatory.catalog import (
    CatalogResult,
    ColumnInfo,
    SchemaProfile,
    build_catalog,
)
from psdl_observatory.roles import ROLE_PATIENT, ROLE_TIME, ROLE_TEXT


def test_build_catalog_over_synthetic_lake(parquet_lake):
    scan = scan_inventory(parquet_lake)
    cat = build_catalog(scan)
    assert isinstance(cat, CatalogResult)

    # --- column catalog ---
    by_name = {c.normalized: c for c in cat.columns}
    # patient_id appears in EHR/labs (schema A, 2 files) AND EHR/vitals (schema B)
    assert "patient_id" in by_name
    pid = by_name["patient_id"]
    assert pid.role == ROLE_PATIENT
    assert pid.file_count == 3          # labs part-0, labs part-1, vitals part-0
    assert pid.schema_count == 2        # schema A and schema B
    # 'text' column (NOTES schema) -> text role
    assert by_name["text"].role == ROLE_TEXT
    # 'value' -> other
    from psdl_observatory.roles import ROLE_OTHER
    assert by_name["value"].role == ROLE_OTHER

    # --- schema profiles ---
    assert len(cat.schemas) == scan.distinct_schema_count  # 3 distinct schemas
    # the NOTES schema profile has a text column -> roles_present includes text
    notes = [s for s in cat.schemas if "text" in s.columns]
    assert len(notes) == 1
    assert ROLE_TEXT in notes[0].roles_present
    # the labs schema (patient_id, value) -> has patient, no encounter
    labs = [s for s in cat.schemas if "value" in s.columns and "patient_id" in s.columns]
    assert len(labs) == 1
    assert ROLE_PATIENT in labs[0].roles_present
    assert labs[0].num_files == 2       # part-0 + part-1 share schema A


def test_build_catalog_role_counts_and_table_kind(parquet_lake):
    scan = scan_inventory(parquet_lake)
    cat = build_catalog(scan)
    for s in cat.schemas:
        # role_counts sums to num_columns
        assert sum(s.role_counts.values()) == s.num_columns
        assert s.table_kind  # non-empty label


def test_build_catalog_empty_scan(tmp_path):
    scan = scan_inventory(tmp_path)  # no parquet files
    cat = build_catalog(scan)
    assert cat.columns == []
    assert cat.schemas == []
