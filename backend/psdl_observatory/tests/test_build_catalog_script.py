"""Smoke test for the DS-facing build_catalog.sh wrapper."""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_catalog.sh"


def test_script_writes_catalog_json(parquet_lake, tmp_path):
    dest = tmp_path / "published"
    # Pass the current interpreter so the script uses this venv's python.
    result = subprocess.run(
        ["bash", str(SCRIPT), str(parquet_lake), str(dest)],
        capture_output=True,
        text=True,
        env={"PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stderr
    out = dest / "catalog.json"
    assert out.exists()
    assert json.loads(out.read_text())["catalog_version"] == "1.1"


def test_script_rejects_missing_root(tmp_path):
    result = subprocess.run(
        ["bash", str(SCRIPT), str(tmp_path / "nope"), str(tmp_path / "out")],
        capture_output=True,
        text=True,
        env={"PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin"},
    )
    assert result.returncode == 2
    assert "not a directory" in result.stderr
