"""Tests for num_rows aggregation, the JSON writer, and the --json CLI."""

import json

from psdl_observatory import scan_inventory
from psdl_observatory.catalog import build_catalog


def test_build_catalog_populates_num_rows(parquet_lake):
    scan = scan_inventory(parquet_lake)
    cat = build_catalog(scan)
    # Every schema profile carries a row total.
    assert all(isinstance(s.num_rows, int) for s in cat.schemas)
    # Each file belongs to exactly one schema signature, so schema row totals
    # sum to the scan's total rows.
    assert sum(s.num_rows for s in cat.schemas) == scan.total_rows
