"""Offline SQL preflight router.

Wraps preflight's pure offline entry point. The connector is hardcoded to None:
Inspector never connects to a database and never executes SQL. With connector=None,
run_preflight builds the report entirely from the static catalog estimate
(query_plan stays None). The preflight offline core is an OPTIONAL dependency
(installed editable in dev; see backend/requirements.txt). When it is absent the
/check endpoint degrades to 503 and the rest of the app is unaffected.
"""
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from preflight import run_preflight
    from preflight.contracts import GeneratedSQL, PreflightReport
    from preflight.catalog.loader import load_catalog
    PREFLIGHT_AVAILABLE = True
except ImportError:  # offline core not installed — endpoints degrade gracefully
    PREFLIGHT_AVAILABLE = False

router = APIRouter()

# Bundled seed schemas shipped with preflight (catalog/schemas/*.yaml).
BUNDLED_CATALOGS: List[str] = ["omop", "epic", "caboodle", "pcornet", "clarity"]
DEFAULT_CATALOG = "omop"


class PreflightCheckRequest(BaseModel):
    sql: str
    dialect: str = "generic"
    catalog_source: str = "omop"


class CatalogsResponse(BaseModel):
    bundled: List[str]
    default: str
    observatory_available: bool
    preflight_available: bool


@router.get("/preflight/catalogs", response_model=CatalogsResponse)
def list_catalogs() -> CatalogsResponse:
    # Read-only, never throws. observatory_available (Observatory-fed catalog) is
    # Plan 3 — hardcoded False. preflight_available lets the UI warn when the
    # optional offline core is missing instead of failing on /check.
    return CatalogsResponse(
        bundled=list(BUNDLED_CATALOGS),
        default=DEFAULT_CATALOG,
        observatory_available=False,
        preflight_available=PREFLIGHT_AVAILABLE,
    )


@router.post("/preflight/check")
def check(req: PreflightCheckRequest):
    if not PREFLIGHT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="preflight offline core is not installed on this server",
        )
    if not req.sql or not req.sql.strip():
        raise HTTPException(status_code=400, detail="sql is required")

    try:
        catalog = load_catalog(req.catalog_source)
    except FileNotFoundError:
        raise HTTPException(
            status_code=400,
            detail=f"unknown catalog '{req.catalog_source}'. valid: {', '.join(BUNDLED_CATALOGS)}",
        )

    generated = GeneratedSQL(query=req.sql, dialect=req.dialect, target=req.catalog_source)

    try:
        # connector=None => fully OFFLINE. Never parameterized.
        report = run_preflight(generated, catalog, connector=None)
    except Exception as exc:  # noqa: BLE001 - surface parse errors as 400
        raise HTTPException(status_code=400, detail=f"SQL parse error: {exc}")

    return report
