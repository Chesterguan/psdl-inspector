"""Synthetic parquet fixtures for Observatory scanner tests.

Builds a small, hermetic parquet lake on disk (no PHI, no network) covering the
cases that matter: nested dirs, multiple schemas, duplicate filenames across
dirs, multi-row-group files.
"""

import pyarrow as pa
import pyarrow.parquet as pq
import pytest


def _write(path, table, row_group_size=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, row_group_size=row_group_size)


@pytest.fixture
def parquet_lake(tmp_path):
    """A synthetic parquet lake at tmp_path. Returns the root Path.

    Layout:
      EHR/labs/part-0.parquet      schema A (patient_id:int64, value:double), 100 rows, 2 row groups
      EHR/labs/part-1.parquet      schema A, 50 rows
      EHR/vitals/part-0.parquet    schema B (patient_id:int64, hr:int64), 30 rows  (dup basename part-0.parquet)
      NOTES/notes-0.parquet        schema C (note_id:int64, text:string), 10 rows
    """
    root = tmp_path / "lake"

    schema_a = pa.table(
        {"patient_id": pa.array(range(100), pa.int64()),
         "value": pa.array([float(i) for i in range(100)], pa.float64())}
    )
    _write(root / "EHR" / "labs" / "part-0.parquet", schema_a, row_group_size=50)  # 100 rows -> 2 row groups

    schema_a_small = pa.table(
        {"patient_id": pa.array(range(50), pa.int64()),
         "value": pa.array([float(i) for i in range(50)], pa.float64())}
    )
    _write(root / "EHR" / "labs" / "part-1.parquet", schema_a_small)

    schema_b = pa.table(
        {"patient_id": pa.array(range(30), pa.int64()),
         "hr": pa.array(range(30), pa.int64())}
    )
    _write(root / "EHR" / "vitals" / "part-0.parquet", schema_b)  # duplicate basename "part-0.parquet"

    schema_c = pa.table(
        {"note_id": pa.array(range(10), pa.int64()),
         "text": pa.array([f"n{i}" for i in range(10)], pa.string())}
    )
    _write(root / "NOTES" / "notes-0.parquet", schema_c)

    return root
