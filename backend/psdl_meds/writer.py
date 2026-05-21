"""Write MEDS shards as single-file Parquet.

Single-shard, in-memory writer suitable for cohorts up to ~50k subjects.
For larger cohorts, M4 will add a streaming/sharded writer; for now we
keep the interface simple and require the caller to hold the row set.
"""

from pathlib import Path
from typing import Iterable, Mapping, Union

import pyarrow as pa
import pyarrow.parquet as pq

from psdl_meds.schema import meds_arrow_schema

_REQUIRED = ("subject_id", "time", "code")


def write_meds_shard(
    rows: Iterable[Mapping],
    out_path: Union[str, Path],
) -> dict:
    """Write `rows` to a MEDS Parquet shard at `out_path`.

    Each row must contain `subject_id` (int), `time` (datetime), `code`
    (string). `numeric_value` (float) is optional and may be `None`.

    Returns a dict with `n_events` and `n_subjects` counts.
    """
    materialized = list(rows)
    if not materialized:
        raise ValueError("write_meds_shard called with no rows")

    for r in materialized:
        for col in _REQUIRED:
            if col not in r or r[col] is None:
                raise ValueError(f"row missing required column: {col!r}")

    schema = meds_arrow_schema()
    columns = {
        "subject_id": [int(r["subject_id"]) for r in materialized],
        "time": [r["time"] for r in materialized],
        "code": [str(r["code"]) for r in materialized],
        "numeric_value": [
            (float(r["numeric_value"]) if r.get("numeric_value") is not None else None)
            for r in materialized
        ],
    }
    table = pa.table(columns, schema=schema)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out)

    return {
        "n_events": table.num_rows,
        "n_subjects": len({r["subject_id"] for r in materialized}),
    }
