"""Test the Inspector /api/meds/preview endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_preview_returns_summary():
    body = {
        "anchors": [
            {
                "psdl_signal": "serum_creatinine",
                "omop_vocabulary": "LOINC",
                "omop_concept_code": "2160-0",
                "expected_unit": "mg/dL",
            }
        ],
        "n": 5,
    }
    resp = client.post("/api/meds/preview", json=body)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["n_events"] == 5
    assert payload["n_subjects"] >= 1
    assert payload["path"].endswith(".parquet")
    assert payload["codes_used"]  # list of code strings used in the preview


def test_preview_rejects_empty_anchors():
    resp = client.post("/api/meds/preview", json={"anchors": [], "n": 5})
    assert resp.status_code == 400


def test_preview_default_row_count():
    body = {
        "anchors": [
            {
                "psdl_signal": "x",
                "omop_vocabulary": "LOINC",
                "omop_concept_code": "1234-5",
            }
        ],
    }
    resp = client.post("/api/meds/preview", json=body)
    assert resp.status_code == 200
    assert resp.json()["n_events"] == 10
