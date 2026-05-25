"""Tests for psdl_observatory.models."""

from psdl_observatory.models import ParquetFileInfo, ScanResult


def test_parquet_file_info_fields():
    info = ParquetFileInfo(
        relative_path="EHR/labs/part-0.parquet",
        size_bytes=1024,
        num_rows=100,
        num_row_groups=2,
        columns=("patient_id", "value"),
        schema_signature="abc123",
    )
    assert info.relative_path == "EHR/labs/part-0.parquet"
    assert info.size_bytes == 1024
    assert info.num_rows == 100
    assert info.num_row_groups == 2
    assert info.columns == ("patient_id", "value")
    assert info.num_columns == 2
    assert info.filename == "part-0.parquet"


def test_scan_result_aggregates():
    files = [
        ParquetFileInfo("a/x.parquet", 10, 5, 1, ("p", "v"), "sig1"),
        ParquetFileInfo("b/x.parquet", 20, 7, 1, ("p", "v"), "sig1"),
        ParquetFileInfo("c/y.parquet", 30, 3, 1, ("p",), "sig2"),
    ]
    r = ScanResult(root="/data", files=files, errors=[])
    assert r.total_files == 3
    assert r.total_rows == 15
    assert r.total_size_bytes == 60
    assert r.distinct_schema_count == 2
    # duplicate basename "x.parquet" appears at a/x and b/x
    dups = r.duplicate_filenames()
    assert dups == {"x.parquet": ["a/x.parquet", "b/x.parquet"]}
