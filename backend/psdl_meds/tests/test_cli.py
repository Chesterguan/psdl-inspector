"""Tests for psdl_meds.cli — `psdl-meds` command-line entry points."""

import csv
import json
import subprocess
import sys
from pathlib import Path


def _run(*args, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "psdl_meds.cli", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_cli_convert_from_csv(tmp_path: Path):
    src = tmp_path / "in.csv"
    out = tmp_path / "out.parquet"
    with src.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject_id", "time", "code", "numeric_value"])
        w.writerow(["42", "2024-03-01T08:00:00", "LOINC/2160-0", "1.5"])
        w.writerow(["43", "2024-03-01T09:00:00", "ICD10CM/N17.9", ""])

    result = _run("convert", "--input", str(src), "--out", str(out), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert out.exists()

    payload = json.loads(result.stdout)
    assert payload["n_events"] == 2
    assert payload["n_subjects"] == 2


def test_cli_preview_from_anchors_json(tmp_path: Path):
    anchors = tmp_path / "anchors.json"
    out = tmp_path / "preview.parquet"
    anchors.write_text(
        json.dumps(
            [
                {
                    "psdl_signal": "serum_creatinine",
                    "omop_vocabulary": "LOINC",
                    "omop_concept_code": "2160-0",
                    "expected_unit": "mg/dL",
                }
            ]
        )
    )

    result = _run(
        "preview", "--anchors", str(anchors), "--out", str(out), "-n", "5",
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["n_events"] == 5


def test_cli_help_exits_zero(tmp_path: Path):
    result = _run("--help", cwd=tmp_path)
    assert result.returncode == 0
    assert "convert" in result.stdout
    assert "preview" in result.stdout
