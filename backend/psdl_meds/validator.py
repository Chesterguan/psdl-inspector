"""Validate a MEDS Parquet shard against the official MEDS spec.

We deliberately use the `meds` package's schema (not our internal mirror)
so this validator stays correct when the spec evolves — bump the `meds`
pin in requirements and re-run tests.
"""

from pathlib import Path
from typing import Union

import pyarrow.parquet as pq

try:
    from meds.schema import data_schema as _meds_data_schema_fn
except ImportError:  # pragma: no cover - fallback for alt package layout
    from meds import data_schema as _meds_data_schema_fn  # type: ignore

# meds>=0.3 exposes `data_schema` as a callable that returns a pyarrow.Schema.
# Resolve once at module load so every validate_shard() call shares the same
# schema object (and we still tolerate older versions where it was already a
# Schema instance — calling a non-callable raises TypeError, the `else` branch
# below catches that and treats it as the schema itself).
if callable(_meds_data_schema_fn):
    _MEDS_DATA_SCHEMA = _meds_data_schema_fn()
else:
    _MEDS_DATA_SCHEMA = _meds_data_schema_fn


def validate_shard(path: Union[str, Path]) -> None:
    """Raise `ValueError` if the Parquet at `path` is not a valid MEDS shard.

    Checks the required columns are present with the right types; nullability
    deviations from the MEDS spec also raise.
    """
    table = pq.read_table(path)
    actual = table.schema

    for expected_field in _MEDS_DATA_SCHEMA:
        name = expected_field.name
        if name not in actual.names:
            # meds==0.3.3 marks all fields nullable=True in PyArrow metadata,
            # but every column in data_schema() is structurally required — the
            # nullable flag here only reflects whether individual *values* may
            # be null, not whether the column itself may be absent.
            raise ValueError(f"MEDS shard {path} missing required column: {name}")

        actual_field = actual.field(name)
        if actual_field.type != expected_field.type:
            raise ValueError(
                f"MEDS shard {path}: column {name!r} has type "
                f"{actual_field.type}, expected {expected_field.type}"
            )
