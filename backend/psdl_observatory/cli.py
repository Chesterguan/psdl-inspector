"""`psdl-observatory` command-line entry point.

    psdl-observatory scan <root> --out <dir> [--html] [--workers N]
    psdl-observatory catalog <root> --out <dir> [--html] [--workers N]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Optional

from psdl_observatory.catalog import build_catalog
from psdl_observatory.catalog_writers import write_catalog_all
from psdl_observatory.report import render_catalog_html, render_html_report
from psdl_observatory.scanner import scan_inventory
from psdl_observatory.writers import write_all


def _cmd_scan(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    if args.workers < 1:
        print(f"error: --workers must be >= 1, got {args.workers}", file=sys.stderr)
        return 2
    out_dir = Path(args.out)
    if out_dir.exists() and not out_dir.is_dir():
        print(f"error: --out exists and is not a directory: {out_dir}", file=sys.stderr)
        return 2
    result = scan_inventory(root, workers=args.workers)
    paths = write_all(result, out_dir)
    if args.html:
        html_path = out_dir / "inventory.html"
        html_path.write_text(render_html_report(result))
        paths["html"] = html_path
    print(f"scanned {result.total_files} parquet files, "
          f"{result.total_rows} rows, {result.distinct_schema_count} distinct schemas, "
          f"{len(result.errors)} errors")
    for label, p in paths.items():
        print(f"  {label}: {p}")
    return 0


def _cmd_catalog(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    if args.workers < 1:
        print(f"error: --workers must be >= 1, got {args.workers}", file=sys.stderr)
        return 2
    out_dir = Path(args.out)
    if out_dir.exists() and not out_dir.is_dir():
        print(f"error: --out exists and is not a directory: {out_dir}", file=sys.stderr)
        return 2
    result = scan_inventory(root, workers=args.workers)
    catalog = build_catalog(result)
    paths = write_catalog_all(catalog, out_dir)
    if args.html:
        html_path = out_dir / "catalog.html"
        html_path.write_text(render_catalog_html(catalog))
        paths["html"] = html_path
    print(f"catalog: {len(catalog.columns)} distinct columns, "
          f"{len(catalog.schemas)} distinct schemas")
    for label, p in paths.items():
        print(f"  {label}: {p}")
    return 0


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="psdl-observatory")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_scan = sub.add_parser("scan", help="Scan a parquet lake (footers only) and write the inventory")
    p_scan.add_argument("root", help="Root directory of the parquet lake")
    p_scan.add_argument("--out", required=True, help="Output directory for the inventory artifacts")
    p_scan.add_argument("--html", action="store_true", help="Also write inventory.html")
    p_scan.add_argument("--workers", type=int, default=8, help="Parallel footer-read workers (default 8)")
    p_scan.set_defaults(func=_cmd_scan)
    p_cat = sub.add_parser("catalog", help="Infer the semantic schema catalog from a parquet lake")
    p_cat.add_argument("root", help="Root directory of the parquet lake")
    p_cat.add_argument("--out", required=True, help="Output directory for the catalog artifacts")
    p_cat.add_argument("--html", action="store_true", help="Also write catalog.html")
    p_cat.add_argument("--workers", type=int, default=8, help="Parallel footer-read workers (default 8)")
    p_cat.set_defaults(func=_cmd_catalog)
    ns = parser.parse_args(list(argv) if argv is not None else None)
    return ns.func(ns)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
