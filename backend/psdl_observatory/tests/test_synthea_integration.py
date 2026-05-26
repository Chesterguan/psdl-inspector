"""Integration test: scan a Synthea-generated parquet EDW.

Skipped unless PSDL_OBSERVATORY_SYNTHEA_EDW points at a parquet lake built by
scripts/make_synthea_edw.py. Keeps CI hermetic while letting us validate the
scanner against a realistic, multi-table 'new EDW'.
"""

import os
from pathlib import Path

import pytest

from psdl_observatory import scan_inventory, write_all

EDW = os.environ.get("PSDL_OBSERVATORY_SYNTHEA_EDW")

pytestmark = pytest.mark.skipif(
    not EDW or not Path(EDW).is_dir(),
    reason="set PSDL_OBSERVATORY_SYNTHEA_EDW to a Synthea parquet lake to run",
)


def test_scan_synthea_edw(tmp_path):
    result = scan_inventory(EDW)
    # a real synthetic EDW has many parquet files across multiple tables/schemas
    assert result.total_files > 5
    assert result.total_rows > 0
    assert result.distinct_schema_count >= 3  # patients/encounters/observations differ
    assert result.errors == []
    # writers succeed end-to-end on real data
    out = write_all(result, tmp_path / "scans")
    assert out["inventory"].exists()
    # sharded tables produce duplicate basenames (e.g. patients-0.parquet patterns)
    # -- at minimum the scan completes and the summary is written
    assert out["summary"].read_text().startswith("PSDL Observatory")
