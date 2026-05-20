"""Tests for psdl_meds.writer — MEDS Parquet shard writer."""

from datetime import datetime
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from psdl_meds.writer import write_meds_shard


def _sample_rows():
    return [
        {
            "subject_id": 1001,
            "time": datetime(2024, 3, 1, 8, 30),
            "code": "LOINC/2160-0",
            "numeric_value": 1.2,
        },
        {
            "subject_id": 1001,
            "time": datetime(2024, 3, 2, 8, 30),
            "code": "LOINC/2160-0",
            "numeric_value": 1.6,
        },
        {
            "subject_id": 1002,
            "time": datetime(2024, 3, 1, 9, 0),
            "code": "ICD10CM/N17.9",
            "numeric_value": None,
        },
    ]


def test_writer_creates_file(tmp_path: Path):
    out = tmp_path / "shard.parquet"
    write_meds_shard(_sample_rows(), out)
    assert out.exists()


def test_writer_returns_counts(tmp_path: Path):
    out = tmp_path / "shard.parquet"
    summary = write_meds_shard(_sample_rows(), out)
    assert summary == {"n_events": 3, "n_subjects": 2}


def test_writer_round_trip_columns(tmp_path: Path):
    out = tmp_path / "shard.parquet"
    write_meds_shard(_sample_rows(), out)
    table = pq.read_table(out)
    assert set(table.column_names) == {"subject_id", "time", "code", "numeric_value"}
    assert table.num_rows == 3


def test_writer_subject_id_is_int64(tmp_path: Path):
    import pyarrow as pa
    out = tmp_path / "shard.parquet"
    write_meds_shard(_sample_rows(), out)
    table = pq.read_table(out)
    assert pa.types.is_int64(table.schema.field("subject_id").type)


def test_writer_rejects_empty_iterable(tmp_path: Path):
    out = tmp_path / "shard.parquet"
    with pytest.raises(ValueError, match="no rows"):
        write_meds_shard([], out)


def test_writer_rejects_missing_required_column(tmp_path: Path):
    bad_rows = [{"subject_id": 1, "time": datetime(2024, 1, 1), "code": "LOINC/2160-0"}]
    # numeric_value is nullable, so omitting it is fine — drop `code` instead.
    really_bad = [{"subject_id": 1, "time": datetime(2024, 1, 1), "numeric_value": 1.0}]
    out = tmp_path / "shard.parquet"
    # Missing optional numeric_value should still succeed (treat as null).
    write_meds_shard(bad_rows, out)
    # Missing required `code` must fail.
    with pytest.raises((ValueError, KeyError)):
        write_meds_shard(really_bad, out)
