"""MEDS column constants + pyarrow schema for shard validation.

Source of truth: the `meds` PyPI package. We mirror its required columns
here for stable internal references; `validator.py` cross-checks our
writes against the installed `meds` schema at the boundary.
"""

import pyarrow as pa

MEDS_COLUMNS: tuple[str, ...] = (
    "subject_id",
    "time",
    "code",
    "numeric_value",
)


def meds_arrow_schema() -> pa.Schema:
    """Return the pyarrow schema for a single MEDS shard."""
    return pa.schema(
        [
            pa.field("subject_id", pa.int64(), nullable=False),
            pa.field("time", pa.timestamp("us"), nullable=False),
            pa.field("code", pa.string(), nullable=False),
            pa.field("numeric_value", pa.float32(), nullable=True),
        ]
    )
