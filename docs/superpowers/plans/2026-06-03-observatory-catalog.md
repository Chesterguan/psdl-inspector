# Observatory Data Catalog (Plan 1 of 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only "Data Catalog" view to Inspector that surfaces an Observatory-scanned parquet-lake catalog (schemas, columns, roles) with provenance + staleness, fed by a DS-generated `catalog.json`.

**Architecture:** The DS generates `catalog.json` out-of-band via the Observatory CLI (`--json`) into a configured directory. The Inspector backend exposes two read-only endpoints that serve from that directory (no DB, no scan-from-app). A new Next.js route renders the catalog. This plan is the foundation for Plan 2 (offline Preflight) and Plan 3 (Observatory→Preflight adapter).

**Tech Stack:** Python 3.9 (psdl_observatory package + FastAPI backend), pytest + FastAPI TestClient, Next.js 14 App Router + TypeScript + Tailwind.

**Spec:** `docs/superpowers/specs/2026-06-03-observatory-catalog-ui-design.md` (Capability 1).

---

## File Structure

- `backend/psdl_observatory/catalog.py` — MODIFY: add `num_rows` to `SchemaProfile`, populate in `build_catalog`.
- `backend/psdl_observatory/catalog_writers.py` — MODIFY: add `write_catalog_json`.
- `backend/psdl_observatory/cli.py` — MODIFY: add `--json` flag to the `catalog` subcommand.
- `backend/psdl_observatory/scripts/build_catalog.sh` — CREATE: DS-facing atomic generation wrapper (committed).
- `backend/psdl_observatory/tests/test_catalog_json.py` — CREATE: tests for `num_rows`, the JSON writer, and the `--json` CLI.
- `backend/psdl_observatory/tests/test_build_catalog_script.py` — CREATE: subprocess smoke test for the script.
- `backend/app/routers/observatory.py` — CREATE: `/api/observatory/status` + `/api/observatory/catalog`.
- `backend/app/main.py` — MODIFY: register the observatory router.
- `backend/tests/test_observatory_router.py` — CREATE: endpoint tests.
- `frontend/src/components/observatory/ProvenanceBar.tsx` — CREATE.
- `frontend/src/components/observatory/SchemaTable.tsx` — CREATE.
- `frontend/src/components/observatory/ColumnTable.tsx` — CREATE.
- `frontend/src/components/observatory/types.ts` — CREATE: shared TS types.
- `frontend/src/app/catalog/page.tsx` — CREATE: the catalog route.
- `frontend/src/app/page.tsx` — MODIFY: add a header link to `/catalog`.

**Note on paths:** the `psdl_observatory` package uses a flat layout — modules live directly at `backend/psdl_observatory/<module>.py` (per `pyproject.toml`: `package-dir = {"psdl_observatory" = "."}`), with tests at `backend/psdl_observatory/tests/` and an existing (tracked, non-ignored) `backend/psdl_observatory/scripts/` dir. All backend test commands assume the venv is active: `cd backend && source .venv/bin/activate`.

---

## Task 1: Add `num_rows` to schema profiles

**Files:**
- Modify: `backend/psdl_observatory/catalog.py`
- Test: `backend/psdl_observatory/tests/test_catalog_json.py`

- [ ] **Step 1: Write the failing test**

Create `backend/psdl_observatory/tests/test_catalog_json.py`:

```python
"""Tests for num_rows aggregation, the JSON writer, and the --json CLI."""

import json

from psdl_observatory import scan_inventory
from psdl_observatory.catalog import build_catalog


def test_build_catalog_populates_num_rows(parquet_lake):
    scan = scan_inventory(parquet_lake)
    cat = build_catalog(scan)
    # Every schema profile carries a row total.
    assert all(isinstance(s.num_rows, int) for s in cat.schemas)
    # Each file belongs to exactly one schema signature, so schema row totals
    # sum to the scan's total rows.
    assert sum(s.num_rows for s in cat.schemas) == scan.total_rows
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && python -m pytest psdl_observatory/tests/test_catalog_json.py::test_build_catalog_populates_num_rows -v`
Expected: FAIL with `AttributeError: 'SchemaProfile' object has no attribute 'num_rows'`

- [ ] **Step 3: Add the field to `SchemaProfile`**

In `catalog.py`, in the `SchemaProfile` dataclass, add `num_rows` after `num_files`:

```python
@dataclass
class SchemaProfile:
    """Semantic profile of one distinct schema signature."""

    schema_signature: str
    num_files: int
    num_rows: int                            # total rows across files of this signature
    columns: List[str]                       # normalized column names
    role_counts: Dict[str, int]              # role -> count of columns
    roles_present: List[str]                 # roles with count > 0 (stable order)
    table_kind: str                          # heuristic label, e.g. 'clinical_notes'
    example_path: str
```

- [ ] **Step 4: Populate it in `build_catalog`**

In `build_catalog`, in the `--- per-schema profiles ---` block, add a row counter and pass it through. Replace the block that builds `sig_files`/`sig_repr` and the `SchemaProfile(...)` construction:

```python
    # --- per-schema profiles (one representative file per signature) ---
    sig_files: Dict[str, int] = Counter()
    sig_rows: Dict[str, int] = Counter()
    sig_repr = {}  # signature -> representative ParquetFileInfo
    for f in scan.files:
        sig_files[f.schema_signature] += 1
        sig_rows[f.schema_signature] += f.num_rows
        sig_repr.setdefault(f.schema_signature, f)
```

and in the `schemas.append(SchemaProfile(...))` call add `num_rows=sig_rows[sig],` directly after `num_files=sig_files[sig],`:

```python
        schemas.append(SchemaProfile(
            schema_signature=sig,
            num_files=sig_files[sig],
            num_rows=sig_rows[sig],
            columns=norm_cols,
            role_counts=counts,
            roles_present=roles_present,
            table_kind=_classify_table_kind(roles_present),
            example_path=f.relative_path,
        ))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && python -m pytest psdl_observatory/tests/test_catalog_json.py::test_build_catalog_populates_num_rows -v`
Expected: PASS

- [ ] **Step 6: Run the existing catalog tests to check nothing broke**

Run: `python -m pytest psdl_observatory/tests/ -k catalog -q`
Expected: PASS (any test that constructs `SchemaProfile` directly must now pass `num_rows`; if a pre-existing test fails for that reason, add `num_rows=0,` to its constructor call.)

- [ ] **Step 7: Commit**

```bash
git add backend/psdl_observatory/catalog.py backend/psdl_observatory/tests/test_catalog_json.py
git commit -m "feat(observatory): add num_rows aggregation to schema profiles"
```

---

## Task 2: JSON catalog writer

**Files:**
- Modify: `backend/psdl_observatory/catalog_writers.py`
- Test: `backend/psdl_observatory/tests/test_catalog_json.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/psdl_observatory/tests/test_catalog_json.py`:

```python
def test_write_catalog_json_shape(parquet_lake, tmp_path):
    from psdl_observatory.catalog_writers import write_catalog_json

    scan = scan_inventory(parquet_lake)
    cat = build_catalog(scan)
    out = tmp_path / "catalog.json"
    write_catalog_json(cat, scan, out, scanned_at="2026-06-03T10:00:00+00:00")

    data = json.loads(out.read_text())
    assert data["catalog_version"] == "1.1"
    prov = data["provenance"]
    assert prov["scanned_at"] == "2026-06-03T10:00:00+00:00"
    assert prov["root"] == str(parquet_lake)
    assert prov["file_count"] == scan.total_files
    assert prov["schema_count"] == scan.distinct_schema_count
    assert isinstance(prov["scanner_version"], str)
    # schemas carry num_rows; columns carry role
    assert all("num_rows" in s for s in data["schemas"])
    assert all("role" in c for c in data["columns"])
    assert len(data["schemas"]) == scan.distinct_schema_count
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && python -m pytest psdl_observatory/tests/test_catalog_json.py::test_write_catalog_json_shape -v`
Expected: FAIL with `ImportError: cannot import name 'write_catalog_json'`

- [ ] **Step 3: Implement the writer**

In `catalog_writers.py`, add imports at the top (after the existing imports) and the function at the end:

```python
import json
from importlib.metadata import PackageNotFoundError, version

from psdl_observatory.models import ScanResult


def _scanner_version() -> str:
    try:
        return version("psdl-observatory")
    except PackageNotFoundError:
        return "unknown"


def write_catalog_json(
    catalog: CatalogResult,
    scan: ScanResult,
    path: Union[str, Path],
    scanned_at: str,
) -> Path:
    """Serialize the catalog + scan provenance to catalog.json (contract v1.1).

    `scanned_at` is passed in (ISO-8601) so callers control the timestamp and the
    output is deterministic for tests; the CLI stamps the real wall-clock time.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "catalog_version": "1.1",
        "provenance": {
            "scanned_at": scanned_at,
            "root": scan.root,
            "file_count": scan.total_files,
            "schema_count": scan.distinct_schema_count,
            "scanner_version": _scanner_version(),
        },
        "schemas": [
            {
                "schema_signature": s.schema_signature,
                "table_kind": s.table_kind,
                "num_files": s.num_files,
                "num_rows": s.num_rows,
                "roles_present": s.roles_present,
                "role_counts": s.role_counts,
                "columns": s.columns,
                "example_path": s.example_path,
            }
            for s in catalog.schemas
        ],
        "columns": [
            {
                "normalized": c.normalized,
                "role": c.role,
                "file_count": c.file_count,
                "schema_count": c.schema_count,
                "example_path": c.example_path,
            }
            for c in catalog.columns
        ],
    }
    path.write_text(json.dumps(payload, indent=2))
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest psdl_observatory/tests/test_catalog_json.py::test_write_catalog_json_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/psdl_observatory/catalog_writers.py backend/psdl_observatory/tests/test_catalog_json.py
git commit -m "feat(observatory): write_catalog_json (contract v1.1 with provenance)"
```

---

## Task 3: `--json` flag on the catalog CLI

**Files:**
- Modify: `backend/psdl_observatory/cli.py`
- Test: `backend/psdl_observatory/tests/test_catalog_json.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/psdl_observatory/tests/test_catalog_json.py`:

```python
def test_cli_catalog_json_emits_file(parquet_lake, tmp_path):
    from psdl_observatory.cli import main

    rc = main(["catalog", str(parquet_lake), "--out", str(tmp_path), "--json"])
    assert rc == 0
    out = tmp_path / "catalog.json"
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["catalog_version"] == "1.1"
    assert data["provenance"]["scanned_at"]  # non-empty timestamp
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && python -m pytest psdl_observatory/tests/test_catalog_json.py::test_cli_catalog_json_emits_file -v`
Expected: FAIL (`catalog.json` not created; `--json` is an unrecognized argument → SystemExit)

- [ ] **Step 3: Add the flag and wire the writer**

In `cli.py`, add the import near the other catalog imports:

```python
from psdl_observatory.catalog_writers import write_catalog_all, write_catalog_json
```

In `_cmd_catalog`, after `paths = write_catalog_all(catalog, out_dir)` and before the `if args.html:` block, add:

```python
    if args.json:
        from datetime import datetime, timezone
        scanned_at = datetime.now(timezone.utc).isoformat()
        paths["json"] = write_catalog_json(
            catalog, result, out_dir / "catalog.json", scanned_at
        )
```

In `main`, register the flag on the `catalog` subparser (next to `--html`):

```python
    p_cat.add_argument("--json", action="store_true", help="Also write catalog.json (contract v1.1)")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest psdl_observatory/tests/test_catalog_json.py -v`
Expected: PASS (all three tests in the file)

- [ ] **Step 5: Commit**

```bash
git add backend/psdl_observatory/cli.py backend/psdl_observatory/tests/test_catalog_json.py
git commit -m "feat(observatory): psdl-observatory catalog --json flag"
```

---

## Task 4: DS generation script (atomic write)

**Files:**
- Create: `backend/psdl_observatory/scripts/build_catalog.sh`
- Test: `backend/psdl_observatory/tests/test_build_catalog_script.py`

- [ ] **Step 1: Write the failing test**

Create `backend/psdl_observatory/tests/test_build_catalog_script.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && python -m pytest psdl_observatory/tests/test_build_catalog_script.py -v`
Expected: FAIL (script does not exist → bash exit 127 / file-not-found)

- [ ] **Step 3: Create the script**

Create `backend/psdl_observatory/scripts/build_catalog.sh`:

```bash
#!/usr/bin/env bash
# Generate an Observatory catalog.json from a parquet lake (footers only, no PHI)
# and publish it atomically into a catalog directory the Inspector backend reads.
#
#   build_catalog.sh <parquet-root> <catalog-dir>
set -euo pipefail

ROOT="${1:?usage: build_catalog.sh <parquet-root> <catalog-dir>}"
DEST="${2:?usage: build_catalog.sh <parquet-root> <catalog-dir>}"

if [ ! -d "$ROOT" ]; then
  echo "error: not a directory: $ROOT" >&2
  exit 2
fi

mkdir -p "$DEST"
# Temp dir on the SAME filesystem as DEST so the final rename is atomic.
TMP="$(mktemp -d "${DEST%/}/.catalog.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

python -m psdl_observatory.cli catalog "$ROOT" --out "$TMP" --json
mv -f "$TMP/catalog.json" "$DEST/catalog.json"
echo "wrote $DEST/catalog.json"
```

Make it executable:

```bash
chmod +x backend/psdl_observatory/scripts/build_catalog.sh
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest psdl_observatory/tests/test_build_catalog_script.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/psdl_observatory/scripts/build_catalog.sh backend/psdl_observatory/tests/test_build_catalog_script.py
git commit -m "feat(observatory): build_catalog.sh DS wrapper with atomic publish"
```

---

## Task 5: Backend read-only endpoints

**Files:**
- Create: `backend/app/routers/observatory.py`
- Test: `backend/tests/test_observatory_router.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_observatory_router.py`:

```python
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
            "schema_count": 2, "scanner_version": "test",
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && python -m pytest tests/test_observatory_router.py -v`
Expected: FAIL with 404s (router not registered yet) — and an import error if `app.main` cannot import the router after Task 6. Run it now to see the 404 failures.

- [ ] **Step 3: Implement the router**

Create `backend/app/routers/observatory.py`:

```python
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
```

- [ ] **Step 4: Run tests (still failing until registered)**

Run: `python -m pytest tests/test_observatory_router.py -v`
Expected: still FAIL (404) — proceed to Task 6 to register, then re-run here.

---

## Task 6: Register the router

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add the import**

In `app/main.py`, change the routers import line to include `observatory`:

```python
from app.routers import validate, outline, export, generate, vocabulary, meds, observatory
```

- [ ] **Step 2: Register it**

After the `meds` router registration line, add:

```python
app.include_router(observatory.router, prefix="/api", tags=["observatory"])
```

- [ ] **Step 3: Run the router tests to verify they pass**

Run: `cd backend && source .venv/bin/activate && python -m pytest tests/test_observatory_router.py -v`
Expected: PASS (all 7 tests)

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/observatory.py backend/app/main.py backend/tests/test_observatory_router.py
git commit -m "feat(backend): read-only /api/observatory status + catalog endpoints"
```

---

## Task 7: Frontend Data Catalog view

No frontend test framework exists in this repo; verification is `tsc --noEmit` + manual. All steps run from `frontend/`.

**Files:**
- Create: `frontend/src/components/observatory/types.ts`, `ProvenanceBar.tsx`, `SchemaTable.tsx`, `ColumnTable.tsx`
- Create: `frontend/src/app/catalog/page.tsx`
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Create shared types**

Create `frontend/src/components/observatory/types.ts`:

```typescript
export interface Provenance {
  scanned_at: string | null;
  root: string | null;
  file_count: number | null;
  schema_count: number | null;
  scan_error_count: number | null;
  scanner_version: string | null;
}

export interface CatalogStatus {
  configured: boolean;
  available: boolean;
  provenance?: Provenance | null;
  stale?: boolean;
  stale_threshold_days?: number;
  reason?: string | null;
}

export interface SchemaProfile {
  schema_signature: string;
  table_kind: string;
  num_files: number;
  num_rows: number;
  roles_present: string[];
  role_counts: Record<string, number>;
  columns: string[];
  example_path: string;
}

export interface ColumnInfo {
  normalized: string;
  role: string;
  file_count: number;
  schema_count: number;
  example_path: string;
}

export interface Catalog {
  catalog_version?: string;
  provenance?: Provenance;
  schemas?: SchemaProfile[];
  columns?: ColumnInfo[];
  available?: boolean;
  reason?: string | null;
}
```

- [ ] **Step 2: Create `ProvenanceBar`**

Create `frontend/src/components/observatory/ProvenanceBar.tsx`:

```tsx
import type { Provenance } from './types';

export default function ProvenanceBar({ provenance, stale }: { provenance?: Provenance | null; stale?: boolean }) {
  if (!provenance) return null;
  const date = provenance.scanned_at ? new Date(provenance.scanned_at).toLocaleDateString() : 'unknown';
  return (
    <div className="flex flex-wrap items-center gap-3 text-sm text-muted">
      <span>Last scanned <span className="text-foreground font-medium">{date}</span></span>
      <span>· {provenance.file_count ?? '?'} files</span>
      <span>· {provenance.schema_count ?? '?'} schemas</span>
      {provenance.scan_error_count ? (
        <span className="text-accent-warning">· {provenance.scan_error_count} unreadable</span>
      ) : null}
      {stale && (
        <span className="px-2 py-0.5 rounded bg-accent-warning/15 text-accent-warning text-xs font-medium">
          ⚠ catalog may be stale
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create `SchemaTable`**

Create `frontend/src/components/observatory/SchemaTable.tsx`:

```tsx
import type { SchemaProfile } from './types';

export default function SchemaTable({ schemas }: { schemas: SchemaProfile[] }) {
  if (schemas.length === 0) return <div className="text-muted text-sm italic py-4">No schemas.</div>;
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-muted border-b border-border">
        <tr>
          <th className="py-2 pr-4">Table kind</th>
          <th className="py-2 pr-4">Files</th>
          <th className="py-2 pr-4">Rows</th>
          <th className="py-2 pr-4">Columns</th>
          <th className="py-2 pr-4">Roles present</th>
        </tr>
      </thead>
      <tbody>
        {schemas.map((s) => (
          <tr key={s.schema_signature} className="border-b border-border/50">
            <td className="py-2 pr-4 font-medium text-foreground">{s.table_kind.replace(/_/g, ' ')}</td>
            <td className="py-2 pr-4">{s.num_files.toLocaleString()}</td>
            <td className="py-2 pr-4">{s.num_rows.toLocaleString()}</td>
            <td className="py-2 pr-4">{s.columns.length}</td>
            <td className="py-2 pr-4">
              <div className="flex flex-wrap gap-1">
                {s.roles_present.map((r) => (
                  <span key={r} className="px-1.5 py-0.5 rounded bg-accent-cyan/10 text-accent-cyan text-xs">{r}</span>
                ))}
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 4: Create `ColumnTable`**

Create `frontend/src/components/observatory/ColumnTable.tsx`:

```tsx
import type { ColumnInfo } from './types';

export default function ColumnTable({ columns }: { columns: ColumnInfo[] }) {
  if (columns.length === 0) return <div className="text-muted text-sm italic py-4">No columns match.</div>;
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-muted border-b border-border">
        <tr>
          <th className="py-2 pr-4">Column</th>
          <th className="py-2 pr-4">Role</th>
          <th className="py-2 pr-4">Files</th>
          <th className="py-2 pr-4">Schemas</th>
          <th className="py-2 pr-4">Example path</th>
        </tr>
      </thead>
      <tbody>
        {columns.map((c) => (
          <tr key={c.normalized} className="border-b border-border/50">
            <td className="py-2 pr-4 font-mono text-foreground">{c.normalized}</td>
            <td className="py-2 pr-4">
              <span className="px-1.5 py-0.5 rounded bg-accent-purple/10 text-accent-purple text-xs">{c.role}</span>
            </td>
            <td className="py-2 pr-4">{c.file_count.toLocaleString()}</td>
            <td className="py-2 pr-4">{c.schema_count.toLocaleString()}</td>
            <td className="py-2 pr-4 font-mono text-xs text-muted truncate max-w-[260px]" title={c.example_path}>{c.example_path}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 5: Create the catalog route**

Create `frontend/src/app/catalog/page.tsx`:

```tsx
'use client';

import { useEffect, useMemo, useState } from 'react';
import ProvenanceBar from '@/components/observatory/ProvenanceBar';
import SchemaTable from '@/components/observatory/SchemaTable';
import ColumnTable from '@/components/observatory/ColumnTable';
import type { Catalog, CatalogStatus } from '@/components/observatory/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8200';

export default function CatalogPage() {
  const [status, setStatus] = useState<CatalogStatus | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [tab, setTab] = useState<'schemas' | 'columns'>('schemas');
  const [query, setQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('');

  useEffect(() => {
    fetch(`${API_BASE}/api/observatory/status`).then((r) => r.json()).then(setStatus).catch(() => setStatus(null));
    fetch(`${API_BASE}/api/observatory/catalog`).then((r) => r.json()).then(setCatalog).catch(() => setCatalog(null));
  }, []);

  const columns = catalog?.columns ?? [];
  const schemas = catalog?.schemas ?? [];
  const roles = useMemo(() => Array.from(new Set(columns.map((c) => c.role))).sort(), [columns]);

  const filteredColumns = useMemo(() => columns.filter(
    (c) => (!query || c.normalized.toLowerCase().includes(query.toLowerCase())) && (!roleFilter || c.role === roleFilter),
  ), [columns, query, roleFilter]);

  const filteredSchemas = useMemo(() => schemas.filter(
    (s) => !query || s.table_kind.includes(query.toLowerCase()) || s.columns.some((c) => c.includes(query.toLowerCase())),
  ), [schemas, query]);

  return (
    <main className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold text-foreground">Institutional Data Catalog</h1>
        <a href="/" className="text-sm text-accent hover:underline">← Back to Inspector</a>
      </div>

      {status && !status.configured && (
        <div className="text-muted text-sm py-8">Data catalog not set up — ask your data team to publish one.</div>
      )}
      {status && status.configured && !status.available && (
        <div className="text-muted text-sm py-8">{status.reason || 'No catalog published yet.'}</div>
      )}

      {status?.available && (
        <>
          <ProvenanceBar provenance={status.provenance} stale={status.stale} />

          <div className="flex flex-wrap items-center gap-3 mt-6 mb-3">
            <div className="flex gap-1">
              <button onClick={() => setTab('schemas')} className={`px-3 py-1.5 rounded text-sm ${tab === 'schemas' ? 'bg-accent text-white' : 'bg-background-tertiary text-muted'}`}>Schemas</button>
              <button onClick={() => setTab('columns')} className={`px-3 py-1.5 rounded text-sm ${tab === 'columns' ? 'bg-accent text-white' : 'bg-background-tertiary text-muted'}`}>Columns</button>
            </div>
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="search…" className="px-3 py-1.5 rounded bg-background-tertiary text-sm text-foreground border border-border" />
            {tab === 'columns' && (
              <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className="px-3 py-1.5 rounded bg-background-tertiary text-sm text-foreground border border-border">
                <option value="">all roles</option>
                {roles.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            )}
          </div>

          <div className="overflow-x-auto">
            {tab === 'schemas' ? <SchemaTable schemas={filteredSchemas} /> : <ColumnTable columns={filteredColumns} />}
          </div>
        </>
      )}
    </main>
  );
}
```

- [ ] **Step 6: Add a header link from the main page**

In `frontend/src/app/page.tsx`, the top header renders action buttons using `lucide-react` icons (e.g. `Github`, `HelpCircle`). Add a catalog link in that header action row. Insert this anchor next to those buttons (it uses the already-imported `Package` icon):

```tsx
<a href="/catalog" title="Institutional Data Catalog" className="flex items-center gap-1.5 text-sm text-muted hover:text-foreground transition-colors">
  <Package className="w-4 h-4" /> Data Catalog
</a>
```

If `Package` is not already imported on the page, it is part of the existing `lucide-react` import block at the top of `page.tsx` — confirm it is in that import list (it is, per the current file) and reuse it.

- [ ] **Step 7: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 8: Manual smoke (optional but recommended)**

With the backend running and `OBSERVATORY_CATALOG_DIR` pointed at a dir containing a generated `catalog.json`, run `npm run dev` and open `http://localhost:9806/catalog`. Verify provenance bar, Schemas/Columns tabs, search, and role filter. With the env unset, verify the "not set up" message.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/observatory frontend/src/app/catalog frontend/src/app/page.tsx
git commit -m "feat(frontend): read-only Observatory data catalog view at /catalog"
```

---

## Definition of Done

- `python -m pytest psdl_observatory/tests/test_catalog_json.py psdl_observatory/tests/test_build_catalog_script.py backend/tests/test_observatory_router.py -v` all pass (run the first two from `backend/`, the third path is `tests/test_observatory_router.py` from `backend/`).
- `psdl-observatory catalog <root> --out <dir> --json` writes a valid `catalog.json` (contract v1.1, with `num_rows` + provenance).
- `scripts/build_catalog.sh` publishes atomically.
- `/api/observatory/status` and `/catalog` serve it with graceful configured/missing/stale/malformed handling.
- `/catalog` renders the browser, read-only, with the not-configured/no-catalog empty states.
- `npx tsc --noEmit` clean.

**Next:** Plan 2 — offline Preflight SQL check (`/api/preflight/check` + Preflight view), then Plan 3 — Observatory→Preflight adapter.
