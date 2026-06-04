import app.routers.preflight as preflight_router
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_catalogs_lists_bundled_sources():
    resp = client.get("/api/preflight/catalogs")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["default"] == "omop"
    assert "omop" in data["bundled"]
    for name in ("epic", "caboodle", "pcornet", "clarity"):
        assert name in data["bundled"]
    assert data["observatory_available"] is False
    assert data["preflight_available"] is True  # editable-installed in dev venv


def test_check_offline_returns_report_with_null_query_plan():
    body = {"sql": "SELECT person_id FROM person", "dialect": "generic", "catalog_source": "omop"}
    resp = client.post("/api/preflight/check", json=body)
    assert resp.status_code == 200, resp.text
    report = resp.json()
    assert report["query_plan"] is None  # offline: connector=None, has_plan=False
    assert report["summary"]["execution_target"]
    assert report["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert report["confidence"] in ("LOW", "MEDIUM", "HIGH")
    assert report["runtime_category"] in ("FAST", "MODERATE", "HEAVY", "EXTREME", "UNKNOWN")
    assert isinstance(report["risk_reasons"], list)
    assert isinstance(report["bottlenecks"], list)
    assert isinstance(report["optimizations"], list)
    assert isinstance(report["notes"], list)
    assert "patients" in report["scale"]


def test_check_rejects_blank_sql():
    resp = client.post("/api/preflight/check", json={"sql": "   ", "dialect": "generic", "catalog_source": "omop"})
    assert resp.status_code == 400, resp.text
    assert "sql is required" in resp.json()["detail"]


def test_check_rejects_unknown_catalog():
    resp = client.post("/api/preflight/check", json={"sql": "SELECT 1 FROM person", "dialect": "generic", "catalog_source": "nope_not_real"})
    assert resp.status_code == 400, resp.text
    assert "unknown catalog" in resp.json()["detail"]


def test_check_invokes_run_preflight_offline_with_connector_none(monkeypatch):
    captured = {}
    calls = {"n": 0}
    real_report = client.post(
        "/api/preflight/check",
        json={"sql": "SELECT person_id FROM person", "dialect": "generic", "catalog_source": "omop"},
    ).json()

    def fake_run_preflight(generated, catalog, **kwargs):
        calls["n"] += 1
        captured.update(kwargs)
        return preflight_router.PreflightReport(**real_report)

    monkeypatch.setattr(preflight_router, "run_preflight", fake_run_preflight)
    resp = client.post(
        "/api/preflight/check",
        json={"sql": "SELECT person_id FROM person", "dialect": "generic", "catalog_source": "omop"},
    )
    assert resp.status_code == 200, resp.text
    assert calls["n"] == 1
    assert "connector" in captured, "run_preflight must be called with an explicit connector kwarg"
    assert captured["connector"] is None  # offline never opens a connection


def test_check_503_when_core_unavailable(monkeypatch):
    monkeypatch.setattr(preflight_router, "PREFLIGHT_AVAILABLE", False)
    resp = client.post(
        "/api/preflight/check",
        json={"sql": "SELECT 1 FROM person", "dialect": "generic", "catalog_source": "omop"},
    )
    assert resp.status_code == 503, resp.text
