"""Tests for psdl_meds.preview — synthetic MEDS rows from anchored signals."""

import pytest

from psdl_meds.preview import synthesize_preview


SAMPLE_ANCHORS = [
    {
        "psdl_signal": "serum_creatinine",
        "omop_vocabulary": "LOINC",
        "omop_concept_code": "2160-0",
        "expected_unit": "mg/dL",
    },
    {
        "psdl_signal": "aki_diagnosis",
        "omop_vocabulary": "ICD10CM",
        "omop_concept_code": "N17.9",
        "expected_unit": None,
    },
]


def test_preview_default_row_count():
    rows = synthesize_preview(SAMPLE_ANCHORS)
    assert len(rows) == 10


def test_preview_custom_row_count():
    rows = synthesize_preview(SAMPLE_ANCHORS, n=4)
    assert len(rows) == 4


def test_preview_uses_anchored_codes():
    rows = synthesize_preview(SAMPLE_ANCHORS, n=10)
    codes = {r["code"] for r in rows}
    assert "LOINC/2160-0" in codes
    assert "ICD10CM/N17.9" in codes


def test_preview_rows_have_required_columns():
    rows = synthesize_preview(SAMPLE_ANCHORS, n=2)
    for r in rows:
        assert {"subject_id", "time", "code"}.issubset(r.keys())


def test_preview_subject_ids_are_synthetic_ints():
    rows = synthesize_preview(SAMPLE_ANCHORS, n=5)
    for r in rows:
        assert isinstance(r["subject_id"], int)
        # Synthetic subjects use a deliberately impossible range so they
        # can never be confused for real PHI.
        assert r["subject_id"] < 0


def test_preview_rejects_empty_anchors():
    with pytest.raises(ValueError, match="anchors"):
        synthesize_preview([], n=10)
