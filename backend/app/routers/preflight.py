"""SQL preflight router.

Wraps preflight's entry point. By default the check is fully OFFLINE
(connector=None): the report is built from the static catalog estimate and no
database is touched. A DS may opt in to a LIVE plan against their own local
database (PREFLIGHT_DB_URL, server-configured): preflight then runs a real
EXPLAIN (metadata only — it never executes the query and never reads rows),
which tightens the estimate and raises confidence. The DB URL is read from the
server environment, never from the client.

The preflight offline core is an OPTIONAL dependency (installed editable in dev;
see backend/requirements.txt). When it is absent the /check endpoint degrades to
503 and the rest of the app is unaffected. The live connector additionally needs
psycopg (the preflight `live` extra).
"""
import os
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


def _live_dsn() -> str:
    """Server-configured local-DB connection string (Postgres). Empty = offline only."""
    return os.environ.get("PREFLIGHT_DB_URL", "")


def _live_available() -> bool:
    """A live EXPLAIN is possible only if the core is present, a DB URL is
    configured on the server, and the psycopg driver is installed."""
    if not PREFLIGHT_AVAILABLE or not _live_dsn():
        return False
    try:
        import psycopg  # noqa: F401
        return True
    except ImportError:
        return False


class PreflightCheckRequest(BaseModel):
    sql: str
    dialect: str = "generic"
    catalog_source: str = "omop"
    # Opt in to a real EXPLAIN against the server-configured local DB. Default is
    # offline (catalog estimate only). The client never supplies DB credentials.
    use_live: bool = False


class CatalogsResponse(BaseModel):
    bundled: List[str]
    default: str
    observatory_available: bool
    preflight_available: bool
    # True when the server has a local DB configured (PREFLIGHT_DB_URL + psycopg),
    # so the UI can offer the "run against my local DB" live-plan option.
    live_db_available: bool


@router.get("/preflight/catalogs", response_model=CatalogsResponse)
def list_catalogs() -> CatalogsResponse:
    # Read-only, never throws. observatory_available (Observatory-fed catalog) is
    # Plan 3 — hardcoded False.
    return CatalogsResponse(
        bundled=list(BUNDLED_CATALOGS),
        default=DEFAULT_CATALOG,
        observatory_available=False,
        preflight_available=PREFLIGHT_AVAILABLE,
        live_db_available=_live_available(),
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

    connector = None
    if req.use_live:
        if not _live_available():
            raise HTTPException(
                status_code=503,
                detail="no local database is configured on this server for a live plan",
            )
        from preflight.connector.postgres_connector import PostgresConnector
        connector = PostgresConnector(_live_dsn())

    generated = GeneratedSQL(query=req.sql, dialect=req.dialect, target=req.catalog_source)

    try:
        # connector=None => OFFLINE catalog estimate. A configured local DB runs a
        # real EXPLAIN (metadata only; never executes the query, never reads rows).
        # A live-plan failure degrades to the offline estimate inside run_preflight
        # and is recorded in report.notes — it does not raise here.
        report = run_preflight(generated, catalog, connector=connector)
    except Exception as exc:  # noqa: BLE001 - surface parse errors as 400
        raise HTTPException(status_code=400, detail=f"SQL parse error: {exc}")

    return report
