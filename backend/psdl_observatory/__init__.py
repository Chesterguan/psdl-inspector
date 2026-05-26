"""psdl_observatory — metadata-only EDW parquet-lake inventory scanner.

Reads parquet footers only (no row data, no PHI). Public API:
    scan_inventory(root, workers=...) -> ScanResult
    write_all(scan_result, out_dir) -> dict[str, Path]
    render_html_report(scan_result) -> str
"""

__version__ = "0.1.0"

from psdl_observatory.models import ParquetFileInfo, ScanResult
from psdl_observatory.scanner import read_parquet_footer, scan_inventory
from psdl_observatory.schema_sig import normalize_columns, schema_signature
from psdl_observatory.writers import (
    write_all,
    write_duplicates_csv,
    write_inventory_csv,
    write_summary_txt,
)
from psdl_observatory.report import render_html_report

__all__ = [
    "ParquetFileInfo",
    "ScanResult",
    "read_parquet_footer",
    "scan_inventory",
    "normalize_columns",
    "schema_signature",
    "write_all",
    "write_inventory_csv",
    "write_duplicates_csv",
    "write_summary_txt",
    "render_html_report",
]
