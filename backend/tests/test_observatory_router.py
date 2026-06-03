"""Tests for the read-only /api/observatory endpoints."""

import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _publish(dir_path, scanned_at):
    (dir_path / "catalog.json").write_text(json.dumps({
        "catalog_version": "1.1",
        "provenance": {
            "scanned_at": scanned_at, "root": "/data", "file_count": 3,
            "schema_count": 2, "scan_error_count": 0, "scanner_version": "test",
        },
        "schemas": [], "columns": [],
    }))


def test_status_not_configured(monkeypatch):
    monkeypatch.delenv("OBSERVATORY_CATALOG_DIR", raising=False)
    j = client.get("/api/observatory/status").json()
    assert j["configured"] is False and j["available"] is False


def test_status_fresh(monkeypatch, tmp_path):
    monkeypatch.setenv("OBSERVATORY_CATALOG_DIR", str(tmp_path))
    _publish(tmp_path, datetime.now(timezone.utc).isoformat())
    j = client.get("/api/observatory/status").json()
    assert j["configured"] and j["available"] and j["stale"] is False
    assert j["provenance"]["file_count"] == 3


def test_status_stale(monkeypatch, tmp_path):
    monkeypatch.setenv("OBSERVATORY_CATALOG_DIR", str(tmp_path))
    monkeypatch.setenv("OBSERVATORY_STALE_DAYS", "90")
    _publish(tmp_path, (datetime.now(timezone.utc) - timedelta(days=120)).isoformat())
    assert client.get("/api/observatory/status").json()["stale"] is True


def test_status_missing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("OBSERVATORY_CATALOG_DIR", str(tmp_path))
    j = client.get("/api/observatory/status").json()
    assert j["configured"] and j["available"] is False


def test_status_malformed(monkeypatch, tmp_path):
    monkeypatch.setenv("OBSERVATORY_CATALOG_DIR", str(tmp_path))
    (tmp_path / "catalog.json").write_text("{ not json")
    j = client.get("/api/observatory/status").json()
    assert j["available"] is False and "unreadable" in j["reason"].lower()


def test_catalog_returns_payload(monkeypatch, tmp_path):
    monkeypatch.setenv("OBSERVATORY_CATALOG_DIR", str(tmp_path))
    _publish(tmp_path, datetime.now(timezone.utc).isoformat())
    j = client.get("/api/observatory/catalog").json()
    assert j["catalog_version"] == "1.1"


def test_catalog_not_configured(monkeypatch):
    monkeypatch.delenv("OBSERVATORY_CATALOG_DIR", raising=False)
    j = client.get("/api/observatory/catalog").json()
    assert j["available"] is False
