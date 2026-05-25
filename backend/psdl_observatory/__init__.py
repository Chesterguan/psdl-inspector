"""psdl_observatory — metadata-only EDW parquet-lake inventory scanner.

Reads parquet footers only (no row data, no PHI). Public API:
    scan_inventory(root, workers=...) -> ScanResult
    write_all(scan_result, out_dir) -> dict[str, Path]
    render_html_report(scan_result) -> str
"""

__version__ = "0.1.0"

# Submodules are imported lazily so the package stays importable during
# incremental TDD (each task adds one module; __init__ re-exports whatever is
# available).  Once all modules exist (Tasks 0-6 complete) every name is live.
try:
    from psdl_observatory.models import ParquetFileInfo, ScanResult
except ImportError:
    pass

try:
    from psdl_observatory.scanner import read_parquet_footer, scan_inventory
except ImportError:
    pass

try:
    from psdl_observatory.schema_sig import normalize_columns, schema_signature
except ImportError:
    pass

try:
    from psdl_observatory.writers import (
        write_all,
        write_duplicates_csv,
        write_inventory_csv,
        write_summary_txt,
    )
except ImportError:
    pass

try:
    from psdl_observatory.report import render_html_report
except ImportError:
    pass

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
