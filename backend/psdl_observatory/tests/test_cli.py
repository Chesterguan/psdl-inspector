"""Tests for the psdl-observatory CLI."""

import os
import subprocess
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # .../backend


def _run(*args, cwd):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_BACKEND_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "psdl_observatory.cli", *args],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


def test_cli_scan_writes_outputs(parquet_lake, tmp_path):
    out = tmp_path / "scans"
    r = _run("scan", str(parquet_lake), "--out", str(out), cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert (out / "parquet_inventory.csv").exists()
    assert (out / "duplicate_filenames.csv").exists()
    assert (out / "scan_summary.txt").exists()
    # stdout summary mentions the file count
    assert "scanned 4 parquet files" in r.stdout


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


def test_cli_workers_zero_errors(parquet_lake, tmp_path):
    r = _run("scan", str(parquet_lake), "--out", str(tmp_path / "scans"), "--workers", "0", cwd=tmp_path)
    assert r.returncode == 2
    assert "workers must be >= 1" in r.stderr


def test_cli_out_is_file_errors(parquet_lake, tmp_path):
    bad_out = tmp_path / "afile"
    bad_out.write_text("x")
    r = _run("scan", str(parquet_lake), "--out", str(bad_out), cwd=tmp_path)
    assert r.returncode == 2
    assert "not a directory" in r.stderr


def test_cli_catalog_writes_outputs(parquet_lake, tmp_path):
    out = tmp_path / "reports"
    r = _run("catalog", str(parquet_lake), "--out", str(out), cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert (out / "column_catalog.csv").exists()
    assert (out / "schema_semantic_catalog.csv").exists()
    assert "columns" in r.stdout  # summary mentions column/schema counts


def test_cli_catalog_html_flag(parquet_lake, tmp_path):
    out = tmp_path / "reports"
    r = _run("catalog", str(parquet_lake), "--out", str(out), "--html", cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert (out / "catalog.html").exists()
    assert "<!DOCTYPE html>" in (out / "catalog.html").read_text()


def test_cli_catalog_bad_root_errors(tmp_path):
    r = _run("catalog", str(tmp_path / "nope"), "--out", str(tmp_path / "r"), cwd=tmp_path)
    assert r.returncode == 2
    assert "not a directory" in r.stderr


def test_cli_help_lists_catalog(tmp_path):
    r = _run("--help", cwd=tmp_path)
    assert r.returncode == 0
    assert "catalog" in r.stdout


def test_cli_catalog_workers_zero_errors(parquet_lake, tmp_path):
    r = _run("catalog", str(parquet_lake), "--out", str(tmp_path / "reports"), "--workers", "0", cwd=tmp_path)
    assert r.returncode == 2
    assert "workers must be >= 1" in r.stderr


def test_cli_catalog_out_is_file_errors(parquet_lake, tmp_path):
    bad_out = tmp_path / "afile"
    bad_out.write_text("x")
    r = _run("catalog", str(parquet_lake), "--out", str(bad_out), cwd=tmp_path)
    assert r.returncode == 2
    assert "not a directory" in r.stderr


def test_cli_catalog_reports_scan_errors(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    root = tmp_path / "lake"
    root.mkdir()
    pq.write_table(pa.table({"patient_id": [1, 2]}), root / "good.parquet")
    (root / "bad.parquet").write_text("not a parquet")
    out = tmp_path / "reports"
    r = _run("catalog", str(root), "--out", str(out), cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert "1 scan error" in r.stdout or "errors" in r.stdout.lower()
    # the corrupt file must not have aborted the catalog of the good file
    assert (out / "column_catalog.csv").exists()
