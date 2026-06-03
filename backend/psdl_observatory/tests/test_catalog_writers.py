"""Tests for the catalog CSV writers."""

import csv

from psdl_observatory.catalog import CatalogResult, ColumnInfo, SchemaProfile
from psdl_observatory.catalog_writers import write_catalog_all
from psdl_observatory.roles import ROLE_PATIENT, ROLE_TEXT


def _sample():
    columns = [
        ColumnInfo("patient_id", ROLE_PATIENT, 3, 2, "EHR/labs/part-0.parquet"),
        ColumnInfo("note_text", ROLE_TEXT, 1, 1, "NOTES/notes-0.parquet"),
    ]
    schemas = [
        SchemaProfile(
            schema_signature="sigA", num_files=2, num_rows=0,
            columns=["patient_id", "value"],
            role_counts={"patient": 1, "other": 1}, roles_present=["patient"],
            table_kind="patient_dimension", example_path="EHR/labs/part-0.parquet",
        ),
    ]
    return CatalogResult(columns=columns, schemas=schemas)


def test_write_catalog_all_creates_two_files(tmp_path):
    out = write_catalog_all(_sample(), tmp_path / "reports")
    assert (tmp_path / "reports" / "column_catalog.csv").exists()
    assert (tmp_path / "reports" / "schema_semantic_catalog.csv").exists()
    assert set(out.keys()) == {"columns", "schemas"}


def test_column_catalog_csv_rows(tmp_path):
    write_catalog_all(_sample(), tmp_path / "reports")
    with open(tmp_path / "reports" / "column_catalog.csv") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    pid = [r for r in rows if r["column"] == "patient_id"][0]
    assert pid["role"] == "patient"
    assert pid["file_count"] == "3"
    assert pid["schema_count"] == "2"
    assert pid["example_path"] == "EHR/labs/part-0.parquet"


def test_schema_semantic_csv_rows(tmp_path):
    write_catalog_all(_sample(), tmp_path / "reports")
    with open(tmp_path / "reports" / "schema_semantic_catalog.csv") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    r = rows[0]
    assert r["schema_signature"] == "sigA"
    assert r["num_files"] == "2"
    assert r["table_kind"] == "patient_dimension"
    assert r["roles_present"] == "patient"
    assert r["columns"] == "patient_id|value"
    assert r["n_patient"] == "1"
    assert r["n_other"] == "1"
