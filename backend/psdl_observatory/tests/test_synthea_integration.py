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
    # Synthea shards are named "{table}-{i}.parquet" so basenames are unique
    # across tables (no duplicate filenames expected); we assert the scan
    # completes cleanly and the summary is written.
    assert out["summary"].read_text().startswith("PSDL Observatory")


def test_build_catalog_synthea_edw(tmp_path):
    from psdl_observatory import build_catalog, scan_inventory, write_catalog_all
    from psdl_observatory.roles import ROLE_PATIENT, ROLE_TIME

    scan = scan_inventory(EDW)
    cat = build_catalog(scan)
    # a real EDW has many distinct columns and several schemas
    assert len(cat.columns) > 10
    assert len(cat.schemas) == scan.distinct_schema_count
    roles_seen = {c.role for c in cat.columns}
    # Synthea tables have patient identifiers and timestamps
    assert ROLE_PATIENT in roles_seen
    assert ROLE_TIME in roles_seen
    # writers succeed end-to-end on real data
    out = write_catalog_all(cat, tmp_path / "reports")
    assert out["columns"].exists() and out["schemas"].exists()
