"""Read-only Observatory data-catalog endpoints.

Serves a DS-generated catalog.json from OBSERVATORY_CATALOG_DIR. The app only
reads this directory and never scans or connects to a database — no DB, no auth,
single-tenant OSS. Env is read per-request so deployment/tests can vary it.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

_CATALOG_FILE = "catalog.json"


def _catalog_dir() -> Optional[str]:
    return os.environ.get("OBSERVATORY_CATALOG_DIR")


def _stale_days() -> int:
    try:
        return int(os.environ.get("OBSERVATORY_STALE_DAYS", "90"))
    except ValueError:
        return 90


def _catalog_path() -> Optional[Path]:
    d = _catalog_dir()
    return Path(d) / _CATALOG_FILE if d else None


class Provenance(BaseModel):
    scanned_at: Optional[str] = None
    root: Optional[str] = None
    file_count: Optional[int] = None
    schema_count: Optional[int] = None
    scan_error_count: Optional[int] = None
    scanner_version: Optional[str] = None


class StatusResponse(BaseModel):
    configured: bool
    available: bool
    provenance: Optional[Provenance] = None
    stale: bool = False
    stale_threshold_days: int = 90
    reason: Optional[str] = None


def _load() -> Dict[str, Any]:
    path = _catalog_path()
    assert path is not None  # callers guard configured/exists first
    with open(path) as f:
        return json.load(f)


def _is_stale(scanned_at: Optional[str]) -> bool:
    if not scanned_at:
        return False
    try:
        ts = datetime.fromisoformat(scanned_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).days > _stale_days()


@router.get("/observatory/status", response_model=StatusResponse)
def observatory_status() -> StatusResponse:
    threshold = _stale_days()
    if not _catalog_dir():
        return StatusResponse(configured=False, available=False, stale_threshold_days=threshold)
    path = _catalog_path()
    if path is None or not path.exists():
        return StatusResponse(configured=True, available=False,
                              stale_threshold_days=threshold,
                              reason="No catalog published yet")
    try:
        data = _load()
    except (json.JSONDecodeError, OSError) as exc:
        return StatusResponse(configured=True, available=False,
                              stale_threshold_days=threshold,
                              reason=f"Catalog unreadable: {exc}")
    major = str(data.get("catalog_version", "")).split(".")[0]
    if major != "1":
        return StatusResponse(configured=True, available=False,
                              stale_threshold_days=threshold,
                              reason=f"Unsupported catalog_version {data.get('catalog_version')}")
    prov = Provenance(**(data.get("provenance") or {}))
    return StatusResponse(configured=True, available=True, provenance=prov,
                          stale=_is_stale(prov.scanned_at),
                          stale_threshold_days=threshold)


@router.get("/observatory/catalog")
def observatory_catalog() -> Dict[str, Any]:
    if not _catalog_dir():
        return {"configured": False, "available": False}
    path = _catalog_path()
    if path is None or not path.exists():
        return {"configured": True, "available": False, "reason": "No catalog published yet"}
    try:
        return _load()
    except (json.JSONDecodeError, OSError) as exc:
        return {"configured": True, "available": False, "reason": f"Catalog unreadable: {exc}"}
