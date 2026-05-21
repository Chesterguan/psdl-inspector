"""Tests for psdl_meds.validator — cross-checks shards against the installed
MEDS spec schema (not our internal mirror)."""

from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from psdl_meds.validator import validate_shard
from psdl_meds.writer import write_meds_shard


def test_validator_accepts_well_formed_shard(tmp_path: Path):
    out = tmp_path / "good.parquet"
    write_meds_shard(
        [
            {
                "subject_id": 1,
                "time": datetime(2024, 1, 1),
                "code": "LOINC/2160-0",
                "numeric_value": 1.1,
            }
        ],
        out,
    )
    # Should not raise.
    validate_shard(out)


def test_validator_rejects_missing_required_column(tmp_path: Path):
    # Hand-craft a shard with `code` column missing.
    bad_path = tmp_path / "bad.parquet"
    table = pa.table(
        {
            "subject_id": pa.array([1], type=pa.int64()),
            "time": pa.array([datetime(2024, 1, 1)], type=pa.timestamp("us")),
        }
    )
    pq.write_table(table, bad_path)

    with pytest.raises(ValueError, match="(?i)code|missing|schema"):
        validate_shard(bad_path)


def test_validator_rejects_wrong_subject_id_type(tmp_path: Path):
    bad_path = tmp_path / "bad_type.parquet"
    table = pa.table(
        {
            "subject_id": pa.array(["str_id"], type=pa.string()),  # wrong type
            "time": pa.array([datetime(2024, 1, 1)], type=pa.timestamp("us")),
            "code": pa.array(["LOINC/2160-0"], type=pa.string()),
        }
    )
    pq.write_table(table, bad_path)

    with pytest.raises(ValueError, match="(?i)subject_id|type|schema"):
        validate_shard(bad_path)
