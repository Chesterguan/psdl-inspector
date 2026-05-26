"""Tests for the static HTML inventory report."""

from psdl_observatory.models import ParquetFileInfo, ScanResult
from psdl_observatory.report import render_html_report


def _result():
    files = [
        ParquetFileInfo("EHR/labs/part-0.parquet", 100, 100, 2, ("patient_id", "value"), "sigA"),
        ParquetFileInfo("EHR/vitals/part-0.parquet", 60, 30, 1, ("patient_id", "hr"), "sigB"),
    ]
    return ScanResult(root="/data/lake", files=files, errors=[])


def test_report_is_html():
    html = render_html_report(_result())
    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert "</html>" in html


def test_report_includes_totals_and_files():
    html = render_html_report(_result())
    assert "Total files" in html
    assert "2" in html  # total files
    assert "EHR/labs/part-0.parquet" in html
    assert "sigA" in html


def test_report_escapes_html_in_paths():
    files = [ParquetFileInfo("weird/<script>.parquet", 1, 1, 1, ("a",), "s")]
    html = render_html_report(ScanResult(root="/r", files=files, errors=[]))
    assert "<script>.parquet" not in html       # raw tag must not appear
    assert "&lt;script&gt;.parquet" in html      # escaped form present
