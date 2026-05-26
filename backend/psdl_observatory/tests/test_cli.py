"""Tests for the psdl-observatory CLI."""

import subprocess
import sys


def _run(*args, cwd):
    return subprocess.run(
        [sys.executable, "-m", "psdl_observatory.cli", *args],
        cwd=cwd, capture_output=True, text=True,
    )


def test_cli_scan_writes_outputs(parquet_lake, tmp_path):
    out = tmp_path / "scans"
    r = _run("scan", str(parquet_lake), "--out", str(out), cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert (out / "parquet_inventory.csv").exists()
    assert (out / "duplicate_filenames.csv").exists()
    assert (out / "scan_summary.txt").exists()
    # stdout summary mentions the file count
    assert "4" in r.stdout


def test_cli_scan_html_flag(parquet_lake, tmp_path):
    out = tmp_path / "scans"
    r = _run("scan", str(parquet_lake), "--out", str(out), "--html", cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert (out / "inventory.html").exists()
    assert "<!DOCTYPE html>" in (out / "inventory.html").read_text()


def test_cli_help_lists_scan(tmp_path):
    r = _run("--help", cwd=tmp_path)
    assert r.returncode == 0
    assert "scan" in r.stdout
