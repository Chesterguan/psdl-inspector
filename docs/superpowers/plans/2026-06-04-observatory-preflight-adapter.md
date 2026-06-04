# Observatory → Preflight Catalog Adapter (Plan 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Let Preflight run against the user's *own* scanned data lake. An adapter converts an Observatory `catalog.json` (which already carries per-schema `num_rows`) into a Preflight `Catalog` with real table row estimates, exposed as a `catalog_source: "observatory"` option alongside the bundled seed schemas. Offline preflight estimates then reflect the actual data instead of illustrative seed defaults.

**Architecture:** A pure adapter `catalog.json` → `preflight.catalog.loader.Catalog` (build the `TableProfile` map directly — no temp files, no DB). The preflight router gains an `observatory` catalog source (resolved from `OBSERVATORY_CATALOG_DIR`); `observatory_available` in `/catalogs` flips true when a readable catalog is present. Everything stays offline (`connector=None` unchanged); this only changes which catalog feeds the static estimate.

**Tech Stack:** Python 3.9 / FastAPI, the `preflight` package (`preflight.catalog.loader.Catalog`/`TableProfile`), pytest + FastAPI TestClient; Next.js + TypeScript (tsc only — no FE test framework).

**Context / contracts:**
- `catalog.json` v1.1 (from the Observatory catalog work): `provenance.scanned_at`, and `schemas[]` each with `num_rows`, `table_kind`, `columns`, `example_path` (a relative parquet path, e.g. `measurement/measurement_0.parquet`).
- Preflight `Catalog(schema, tables: {name→TableProfile}, joins, columns, default_dialect, stats_as_of)`; `TableProfile(name, category, volume, risk, row_estimate)`; lookups are case-insensitive by table name. The query planner needs **table names** — Observatory keys by schema signature, so the adapter derives a table name from the first path segment of `example_path` (best-effort; see Task 1).

**Honest limitations (carry into the plan):**
- Table names are derived from parquet paths; a lake whose directory layout doesn't match the SQL's table names will leave tables `unknown` (Preflight degrades — lower `known_ratio`). This is acceptable and already how Preflight handles unknown tables.
- Observatory has no join-cardinality or column-selectivity data, so the adapter emits `joins={}` and `columns={}`. The win is **real per-table row counts**; join fan-out / selectivity stay at Preflight's defaults.

---

## File Structure

| Path | Create/Modify | Responsibility |
|---|---|---|
| `backend/app/services/observatory_to_preflight.py` | Create | Pure adapter: `build_preflight_catalog(catalog_dict)` + `load_observatory_catalog(dir)`. |
| `backend/tests/test_observatory_to_preflight.py` | Create | Adapter unit tests (table-name derivation, row estimates, missing/bad input). |
| `backend/app/routers/preflight.py` | Modify | `observatory_available` true when a catalog is present; `catalog_source="observatory"` resolves via the adapter. |
| `backend/tests/test_preflight_router.py` | Modify | Router tests for the observatory source. |
| `frontend/src/components/preflight/SqlInput.tsx` | Modify | Add an `observatory` option to the catalog dropdown when available. |

---

## Task 1 — Adapter: `catalog.json` → Preflight `Catalog`

**Files:** Create `backend/app/services/observatory_to_preflight.py`; Test `backend/tests/test_observatory_to_preflight.py`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_observatory_to_preflight.py`:

```python
from app.services.observatory_to_preflight import build_preflight_catalog

CATALOG = {
    "catalog_version": "1.1",
    "provenance": {"scanned_at": "2026-06-04T00:00:00+00:00"},
    "schemas": [
        {"table_kind": "coded_clinical_events", "num_rows": 158386692,
         "columns": ["person_id", "measurement_concept_id"], "example_path": "measurement/measurement_0.parquet"},
        {"table_kind": "patient_dimension", "num_rows": 364630,
         "columns": ["person_id"], "example_path": "person/person_0.parquet"},
    ],
    "columns": [],
}


def test_build_catalog_maps_tables_and_real_row_estimates():
    cat = build_preflight_catalog(CATALOG)
    assert cat.schema == "observatory"
    assert cat.stats_as_of == "2026-06-04T00:00:00+00:00"
    # Table names derived from example_path; real row counts become row_estimate.
    assert cat.is_known("measurement")
    assert cat.profile("measurement").row_estimate == 158386692
    assert cat.profile("measurement").effective_rows() == 158386692
    assert cat.profile("person").row_estimate == 364630
    # A huge clinical-event table is flagged high-volume / high-risk.
    assert cat.profile("measurement").volume == "huge"
    assert cat.profile("measurement").risk in ("high", "very_high")
    # Unknown tables degrade gracefully.
    assert not cat.is_known("drug_exposure")


def test_duplicate_table_names_sum_rows():
    cat = build_preflight_catalog({
        "provenance": {"scanned_at": None},
        "schemas": [
            {"table_kind": "coded_clinical_events", "num_rows": 100, "columns": ["a"], "example_path": "measurement/p0.parquet"},
            {"table_kind": "coded_clinical_events", "num_rows": 50, "columns": ["a"], "example_path": "measurement/p1.parquet"},
        ],
    })
    assert cat.profile("measurement").row_estimate == 150
```

- [ ] **Step 2: Run it (expect fail)** — `cd backend && source .venv/bin/activate && python -m pytest tests/test_observatory_to_preflight.py -q`
Expected: `ModuleNotFoundError: app.services.observatory_to_preflight`.

- [ ] **Step 3: Implement the adapter** — create `backend/app/services/observatory_to_preflight.py`:

```python
"""Adapt an Observatory catalog.json into a Preflight Catalog.

Pure data transformation (no DB). Preflight is an optional dependency, so this
module is imported lazily by the router only when preflight is available.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from preflight.catalog.loader import Catalog, TableProfile

_CATALOG_FILE = "catalog.json"


def _table_name(example_path: str) -> Optional[str]:
    """Best-effort logical table name = first path segment of the example parquet
    path (e.g. 'measurement/measurement_0.parquet' -> 'measurement'). Falls back to
    the basename without extension if there is no directory component."""
    if not example_path:
        return None
    norm = example_path.replace("\\", "/").strip("/")
    if not norm:
        return None
    head = norm.split("/")[0]
    if head.endswith(".parquet"):
        head = head[: -len(".parquet")]
    return head or None


def _volume(num_rows: int) -> str:
    if num_rows >= 1_000_000_000:
        return "huge"
    if num_rows >= 50_000_000:
        return "large"
    if num_rows >= 2_000_000:
        return "medium"
    if num_rows >= 100_000:
        return "small"
    return "tiny"


# table_kind (Observatory heuristic) -> (preflight category, base risk)
_KIND = {
    "coded_clinical_events": ("clinical_event", "high"),
    "encounter_events": ("clinical_event", "high"),
    "clinical_notes": ("clinical_event", "high"),
    "encounter_dimension": ("encounter", "medium"),
    "patient_dimension": ("demographics", "low"),
    "reference_or_other": ("unknown", "low"),
}


def build_preflight_catalog(catalog: Dict[str, Any]) -> Catalog:
    """Build a Preflight Catalog from an Observatory catalog.json dict.

    Real per-table row counts (schemas[].num_rows) become row_estimate. Join
    cardinality and column selectivity are not available from a footer scan, so
    joins/columns are left empty (Preflight uses its defaults for those)."""
    rows: Dict[str, int] = {}
    kinds: Dict[str, str] = {}
    for s in catalog.get("schemas") or []:
        name = _table_name(s.get("example_path", ""))
        if not name:
            continue
        key = name.lower()
        rows[key] = rows.get(key, 0) + int(s.get("num_rows") or 0)
        kinds.setdefault(key, s.get("table_kind", "reference_or_other"))

    tables: Dict[str, TableProfile] = {}
    for key, n in rows.items():
        category, risk = _KIND.get(kinds.get(key, ""), ("unknown", "unknown"))
        # A huge clinical-event table is the classic runaway-scan risk.
        if category == "clinical_event" and n >= 1_000_000_000:
            risk = "very_high"
        tables[key] = TableProfile(
            name=key, category=category, volume=_volume(n), risk=risk, row_estimate=n,
        )

    scanned_at = (catalog.get("provenance") or {}).get("scanned_at")
    return Catalog(schema="observatory", tables=tables, joins={}, columns={},
                   stats_as_of=scanned_at)


def load_observatory_catalog(catalog_dir: Optional[str]) -> Optional[Catalog]:
    """Read catalog.json from catalog_dir and adapt it. Returns None when the
    directory is unset, the file is absent/unreadable, or the version is
    unsupported — callers treat None as 'observatory source not available'."""
    if not catalog_dir:
        return None
    path = os.path.join(catalog_dir, _CATALOG_FILE)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if str(data.get("catalog_version", "")).split(".")[0] != "1":
        return None
    return build_preflight_catalog(data)
```

- [ ] **Step 4: Run it (expect pass)** — `python -m pytest tests/test_observatory_to_preflight.py -q` → `2 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/extraSupply/Projects/psdl-inspector && git add backend/app/services/observatory_to_preflight.py backend/tests/test_observatory_to_preflight.py && git commit -m "feat(preflight): observatory catalog.json -> Preflight Catalog adapter

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2 — Router: expose the `observatory` catalog source

**Files:** Modify `backend/app/routers/preflight.py`; Test (append) `backend/tests/test_preflight_router.py`.

- [ ] **Step 1: Write the failing tests** — append to `backend/tests/test_preflight_router.py`:

```python
import json


def _write_obs_catalog(dir_path):
    (dir_path / "catalog.json").write_text(json.dumps({
        "catalog_version": "1.1",
        "provenance": {"scanned_at": "2026-06-04T00:00:00+00:00"},
        "schemas": [
            {"table_kind": "coded_clinical_events", "num_rows": 158386692,
             "columns": ["person_id", "measurement_concept_id"],
             "example_path": "measurement/measurement_0.parquet"},
            {"table_kind": "patient_dimension", "num_rows": 364630,
             "columns": ["person_id"], "example_path": "person/person_0.parquet"},
        ],
        "columns": [],
    }))


def test_catalogs_observatory_available_with_catalog(monkeypatch, tmp_path):
    monkeypatch.setenv("OBSERVATORY_CATALOG_DIR", str(tmp_path))
    _write_obs_catalog(tmp_path)
    data = client.get("/api/preflight/catalogs").json()
    assert data["observatory_available"] is True


def test_catalogs_observatory_unavailable_without_dir(monkeypatch):
    monkeypatch.delenv("OBSERVATORY_CATALOG_DIR", raising=False)
    assert client.get("/api/preflight/catalogs").json()["observatory_available"] is False


def test_check_uses_observatory_catalog(monkeypatch, tmp_path):
    monkeypatch.setenv("OBSERVATORY_CATALOG_DIR", str(tmp_path))
    _write_obs_catalog(tmp_path)
    resp = client.post("/api/preflight/check", json={
        "sql": "SELECT person_id FROM measurement", "dialect": "generic",
        "catalog_source": "observatory"})
    assert resp.status_code == 200, resp.text
    # Real scanned row count flows into the estimate.
    assert resp.json()["scale"]["events"] == 158386692


def test_check_observatory_400_when_unavailable(monkeypatch, tmp_path):
    monkeypatch.setenv("OBSERVATORY_CATALOG_DIR", str(tmp_path))  # empty dir, no catalog.json
    resp = client.post("/api/preflight/check", json={
        "sql": "SELECT 1 FROM person", "dialect": "generic", "catalog_source": "observatory"})
    assert resp.status_code == 400
    assert "observatory" in resp.json()["detail"].lower()
```

- [ ] **Step 2: Run them (expect fail)** — `python -m pytest tests/test_preflight_router.py -q` (the four new tests fail: `observatory_available` is hardcoded False; `catalog_source="observatory"` hits the unknown-catalog 400 path).

- [ ] **Step 3: Wire the router** — in `backend/app/routers/preflight.py`:

Add an env reader near `_live_dsn`:

```python
def _observatory_dir() -> str:
    return os.environ.get("OBSERVATORY_CATALOG_DIR", "")
```

In `list_catalogs`, compute availability (lazy import so the optional dep stays optional):

```python
    obs_available = False
    if PREFLIGHT_AVAILABLE and _observatory_dir():
        from app.services.observatory_to_preflight import load_observatory_catalog
        obs_available = load_observatory_catalog(_observatory_dir()) is not None
    return CatalogsResponse(
        bundled=list(BUNDLED_CATALOGS),
        default=DEFAULT_CATALOG,
        observatory_available=obs_available,
        preflight_available=PREFLIGHT_AVAILABLE,
        live_db_available=_live_available(),
    )
```

In `check`, replace the catalog-resolution block (the `try: catalog = load_catalog(...)`) with:

```python
    if req.catalog_source == "observatory":
        from app.services.observatory_to_preflight import load_observatory_catalog
        catalog = load_observatory_catalog(_observatory_dir())
        if catalog is None:
            raise HTTPException(
                status_code=400,
                detail="observatory catalog is not available (set OBSERVATORY_CATALOG_DIR and publish a catalog.json)",
            )
    else:
        try:
            catalog = load_catalog(req.catalog_source)
        except FileNotFoundError:
            raise HTTPException(
                status_code=400,
                detail=f"unknown catalog '{req.catalog_source}'. valid: {', '.join(BUNDLED_CATALOGS)}, observatory",
            )
```

- [ ] **Step 4: Run pass** — `python -m pytest tests/test_preflight_router.py -q` (all green) and `python -m pytest -q -m "not integration"` (no regressions).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/preflight.py backend/tests/test_preflight_router.py && git commit -m "feat(preflight): add 'observatory' catalog source (real scanned-lake row counts)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3 — Frontend: offer the `observatory` catalog when available

**Files:** Modify `frontend/src/components/preflight/SqlInput.tsx`. Verify with `npx tsc --noEmit` (no FE test framework).

- [ ] **Step 1: Add the option** — in `SqlInput.tsx`, where the catalog `<select>` renders `bundled.map(...)`, prepend an observatory option when the server reports it. Add near the top of the component body:

```tsx
  const obsAvailable = catalogs?.observatory_available ?? false;
```

and change the catalog `<select>`'s options to include it first:

```tsx
            <select
              className="ml-2 bg-background text-foreground border border-border rounded px-2 py-1"
              value={catalogSource}
              onChange={(e) => onCatalogChange(e.target.value)}
            >
              {obsAvailable && <option value="observatory">observatory (scanned lake)</option>}
              {bundled.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
```

- [ ] **Step 2: Typecheck** — `cd frontend && npx tsc --noEmit` → clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/preflight/SqlInput.tsx && git commit -m "feat(preflight): offer the observatory (scanned-lake) catalog in the UI

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Definition of Done
- `build_preflight_catalog` + `load_observatory_catalog` adapt a v1.1 `catalog.json` into a Preflight `Catalog` with real per-table row estimates; unknown/derivation edge cases degrade gracefully.
- `/api/preflight/catalogs` reports `observatory_available` correctly; `POST /check` with `catalog_source="observatory"` runs against the scanned lake's real row counts and 400s when unavailable.
- Default behaviour unchanged: offline by default, bundled catalogs still work, no DB connection added.
- Backend suite + `tsc` green.

## Out of scope
- Join-cardinality / column-selectivity inference from the scan (footer scans don't carry these).
- Any change to the live-DB `EXPLAIN` path or the offline/bundled defaults.
- Auto-selecting `observatory` as the default catalog (kept opt-in).
