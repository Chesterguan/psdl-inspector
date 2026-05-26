"""Tests for the parquet-footer scanner."""

import pyarrow as pa
import pyarrow.parquet as pq

from psdl_observatory.scanner import read_parquet_footer, scan_inventory


def test_read_footer_single_file(tmp_path):
    p = tmp_path / "sub" / "f.parquet"
    p.parent.mkdir(parents=True)
    pq.write_table(
        pa.table({"patient_id": pa.array([1, 2], pa.int64()),
                  "value": pa.array([1.0, 2.0], pa.float64())}),
        p, row_group_size=1,
    )
    info = read_parquet_footer(p, root=tmp_path)
    assert info.relative_path == "sub/f.parquet"
    assert info.num_rows == 2
    assert info.num_row_groups == 2
    assert info.columns == ("patient_id", "value")
    assert info.size_bytes > 0
    assert len(info.schema_signature) == 16


def test_scan_inventory_walks_and_dedups(parquet_lake):
    result = scan_inventory(parquet_lake)
    assert result.total_files == 4
    assert result.total_rows == 100 + 50 + 30 + 10
    # two distinct schemas in EHR/labs (A) vs vitals (B) vs notes (C) = 3 distinct
    assert result.distinct_schema_count == 3
    # the two EHR/labs files share schema A -> same signature
    labs = sorted(f for f in result.files if f.relative_path.startswith("EHR/labs"))
    assert labs[0].schema_signature == labs[1].schema_signature
    # duplicate basename "part-0.parquet" across EHR/labs and EHR/vitals
    dups = result.duplicate_filenames()
    assert "part-0.parquet" in dups
    assert sorted(dups["part-0.parquet"]) == ["EHR/labs/part-0.parquet", "EHR/vitals/part-0.parquet"]


def test_scan_inventory_records_errors_for_bad_parquet(tmp_path):
    # a non-parquet file with a .parquet extension should be recorded as an error, not crash
    bad = tmp_path / "broken.parquet"
    bad.write_text("not a parquet file")
    result = scan_inventory(tmp_path)
    assert result.total_files == 0
    assert len(result.errors) == 1
    assert result.errors[0][0] == "broken.parquet"


def test_scan_inventory_empty_dir(tmp_path):
    result = scan_inventory(tmp_path)
    assert result.total_files == 0
    assert result.errors == []
