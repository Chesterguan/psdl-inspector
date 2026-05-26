"""Tests for inventory output writers."""

import csv

from psdl_observatory.models import ParquetFileInfo, ScanResult
from psdl_observatory.writers import write_all


def _sample_result(root):
    files = [
        ParquetFileInfo("EHR/labs/part-0.parquet", 100, 100, 2, ("patient_id", "value"), "sigA"),
        ParquetFileInfo("EHR/labs/part-1.parquet", 80, 50, 1, ("patient_id", "value"), "sigA"),
        ParquetFileInfo("EHR/vitals/part-0.parquet", 60, 30, 1, ("patient_id", "hr"), "sigB"),
    ]
    return ScanResult(root=str(root), files=files, errors=[("bad.parquet", "ArrowInvalid: x")])


def test_write_all_creates_three_files(tmp_path):
    out = write_all(_sample_result(tmp_path), tmp_path / "scans")
    assert (tmp_path / "scans" / "parquet_inventory.csv").exists()
    assert (tmp_path / "scans" / "duplicate_filenames.csv").exists()
    assert (tmp_path / "scans" / "scan_summary.txt").exists()
    assert set(out.keys()) == {"inventory", "duplicates", "summary"}


def test_inventory_csv_has_row_per_file(tmp_path):
    write_all(_sample_result(tmp_path), tmp_path / "scans")
    with open(tmp_path / "scans" / "parquet_inventory.csv") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3
    assert rows[0]["relative_path"] == "EHR/labs/part-0.parquet"
    assert rows[0]["num_rows"] == "100"
    assert rows[0]["schema_signature"] == "sigA"
    assert rows[0]["columns"] == "patient_id|value"


def test_duplicates_csv_lists_shared_basenames(tmp_path):
    write_all(_sample_result(tmp_path), tmp_path / "scans")
    with open(tmp_path / "scans" / "duplicate_filenames.csv") as f:
        rows = list(csv.DictReader(f))
    # part-0.parquet appears in EHR/labs and EHR/vitals
    assert len(rows) == 1
    assert rows[0]["filename"] == "part-0.parquet"
    assert rows[0]["count"] == "2"


def test_summary_txt_reports_totals(tmp_path):
    write_all(_sample_result(tmp_path), tmp_path / "scans")
    txt = (tmp_path / "scans" / "scan_summary.txt").read_text()
    assert "Total files: 3" in txt
    assert "Total rows: 180" in txt
    assert "Distinct schemas: 2" in txt
    assert "Errors: 1" in txt
    assert "bad.parquet: ArrowInvalid: x" in txt
