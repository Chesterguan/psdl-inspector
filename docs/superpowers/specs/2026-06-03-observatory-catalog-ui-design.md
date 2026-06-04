# Design: Observatory Data Catalog + Offline Preflight in the Inspector UI

*Date: 2026-06-03*
*Status: Approved (design)*
*Affects: psdl-inspector (frontend + backend), psdl-observatory, psdl-workbench-preflight (offline core, as a dependency)*

This is an **update to the already-published OSS Inspector**, not a greenfield build.

## Problem

A clinical data scientist (DS) using Inspector has no in-app way to (a) see what
data their institution actually holds, or (b) know the cost/risk of a study query
*before* running it against a shared EDW. Both are core to the DS's real workflow.

Two existing pieces make this possible without Inspector overstepping its role:

- **`psdl_observatory`** scans a parquet lake (footers only, no PHI) and produces a
  semantic schema catalog — what schemas/columns exist and each column's structural
  role.
- **`psdl-workbench-preflight`** is a deterministic, zero-LLM SQL pre-execution
  analyzer: given a SQL query + a metadata catalog (no DB needed), it reports
  lineage, scale/cost, risk, bottlenecks, optimization fixes, and a go/no-go
  verdict — **without executing the query**.

This update embeds both into Inspector as **read-only, offline, single-user**
features. The DS brings their own SQL; Inspector vets it offline. Inspector never
chooses tables, writes SQL, binds data, or touches PHI.

## Scope (why this is bounded the way it is)

This feature is deliberately **offline, catalog-only, single-user**: no auth, no DB,
no live database connection, no PHI, no LLM.

Explicitly **out of scope** (not built here): live connectors at scale, batch
worklists, role-based / governed catalogs, scheduled scans, multi-source
`datasetSpec` binding, and hosting. Those are larger, separate concerns and don't
belong in this read-only, single-user surface.

## Constraints (from the codebase)

- Inspector is **single-tenant, no auth, no DB** (`backend/app/routers/meds.py`:
  "No DB, no auth — Inspector is single-tenant OSS"). We do **not** add auth.
- `backend/scripts/` is **gitignored**. Shipped tooling lives inside the committed
  `psdl_observatory` package.
- Institutional data already ships via a configured path (the OMOP vocab DBs); the
  catalog follows the same model.
- Preflight dependency: Inspector imports only Preflight's **offline core**
  (`run_preflight(..., connector=None)`; deps: sqlglot, duckdb, pydantic, pyyaml).
  Live connectors are NOT used in Inspector.

## Architecture

```
DS (out-of-band, optional)                Inspector app (read-only, offline)
──────────────────────────                ──────────────────────────────────
parquet lake ─> psdl-observatory ─> catalog.json ─> GET /api/observatory/*  ─> Catalog browser
  (footers)        catalog --json        │
                                         └──(adapter)──> Preflight Catalog ┐
                                                                          ├─> POST /api/preflight/check ─> Preflight view
DS's own SQL ─────────────────────────────────────────────────────────────┘   (connector=None, offline)
bundled schema catalogs (omop/epic/...) ──────────────────────────────────┘
```

The app only ever **reads** the catalog directory and **never connects to a
database**. Those two structural absences are what keep it within the OSS/individual
boundary.

---

## Capability 1 — Observatory Data Catalog (read-only browser)

### Generation (DS, out-of-band)

```bash
psdl_observatory/scripts/build_catalog.sh /data/edw/parquet "$OBSERVATORY_CATALOG_DIR"
# wraps: psdl-observatory catalog <root> --out <dir> --json   (footer-only, no PHI)
```

- New JSON writer in `psdl_observatory/catalog_writers.py`; new `--json` flag in
  `psdl_observatory/cli.py`.
- Script (committed, inside the package) validates the root, runs the CLI, and writes
  `catalog.json` **atomically** (temp file + rename) so the backend never reads a
  half-written file.

### Data contract — `catalog.json`

Serialization of the existing `CatalogResult` (`columns[]`, `schemas[]`) plus a
`provenance` block, **extended with per-schema row totals** (needed by Capability 2):

```json
{
  "catalog_version": "1.1",
  "provenance": {
    "scanned_at": "2026-06-03T10:00:00Z",   // stamped by the JSON writer at gen time
    "root": "/data/edw/parquet",            // ScanResult.root
    "file_count": 1284,                      // ScanResult.total_files
    "schema_count": 47,                      // ScanResult.distinct_schema_count
    "scan_error_count": 0,                    // len(ScanResult.errors) — files that failed to parse
    "scanner_version": "psdl-observatory x.y.z"   // psdl_observatory package version
  },
  "schemas": [
    { "schema_signature": "…", "table_kind": "encounter_events", "num_files": 312,
      "num_rows": 41000000,                  // NEW: summed from ParquetFileInfo.num_rows
      "roles_present": ["patient","encounter","time"], "role_counts": {…},
      "columns": ["person_id","visit_start_date","…"], "example_path": "…" }
  ],
  "columns": [
    { "normalized": "person_id", "role": "patient", "file_count": 980,
      "schema_count": 41, "example_path": "…" }
  ]
}
```

`catalog_version` guards against format drift. Field names map 1:1 to `ColumnInfo`
and `SchemaProfile` in `psdl_observatory/catalog.py`; `num_rows` is a new aggregate.

### Backend (`backend/app/routers/observatory.py`)

- **`GET /api/observatory/status`** — `{ configured, available, provenance, stale,
  stale_threshold_days }`. Drives the header badge / empty states.
- **`GET /api/observatory/catalog`** — full `catalog.json`; UI filters client-side.

Config (env): `OBSERVATORY_CATALOG_DIR` (unset ⇒ feature dormant),
`OBSERVATORY_STALE_DAYS` (default 90).

### Error / edge handling — graceful, never a scary 500

| Condition | Response | UI shows |
|---|---|---|
| Dir not configured | `status.configured=false` | "Data catalog not set up — ask your data team" |
| `catalog.json` missing | `configured=true, available=false` | "No catalog published yet" |
| Malformed / version mismatch | `available=false, reason` | "Catalog unreadable" + reason |
| OK but old | `available=true, stale=true` | catalog + amber "may be stale" badge |

Staleness: `stale = (now - provenance.scanned_at) > OBSERVATORY_STALE_DAYS`.

### Frontend

Top-level `/catalog` view, **outside** the Input→Preview→Export wizard (reference
material). Components under `frontend/src/components/observatory/`: `CatalogView`,
`SchemaTable`, `ColumnTable`, `ProvenanceBar`. No edit/scan affordance — read-only is
structural. Renders the empty/not-configured/unreadable states from `/status`.

---

## Capability 2 — Offline Preflight SQL Check

### Backend (`backend/app/routers/preflight.py`)

- **`POST /api/preflight/check`** — body `{ sql, dialect, catalog_source }`:
  - Build a `GeneratedSQL(query=sql, dialect=dialect)`.
  - Resolve the catalog (see sources below) into a Preflight `Catalog`.
  - Call `run_preflight(sql, catalog, connector=None)` — **always offline**.
  - Return the `PreflightReport` (already a Pydantic model) as JSON.
- **`GET /api/preflight/catalogs`** — list selectable catalog sources (bundled schema
  names + whether an Observatory catalog is available).

### Catalog sources

1. **Bundled schema catalogs (primary, always available):** `omop`, `epic`,
   `caboodle`, `pcornet`, `clarity` — shipped with Preflight. Works out of the box,
   no Observatory scan required. This is the default and the robust path.
2. **Observatory-generated catalog (optional enhancement):** an adapter
   (`backend/app/services/observatory_to_preflight.py`) converts `catalog.json` →
   Preflight `Catalog`, so checks use the DS's **real** lake with **real row counts**
   (`schemas[].num_rows`) instead of seed defaults. Best-effort:
   - `row_estimate` ← real `num_rows` (the high-value part).
   - `category` / `volume` / `risk` ← derived from `table_kind` + row-count buckets.
   - Table identity: Observatory keys by schema/columns, not logical table names, so
     the adapter maps best-effort; unmapped tables simply lower Preflight's
     `known_ratio` (and thus confidence) — Preflight already degrades gracefully.

### Frontend

A **Preflight** view (route `/preflight`, or a tab on `/catalog`): a SQL textarea +
dialect/catalog selectors → renders the report. Components under
`frontend/src/components/preflight/`: `SqlInput`, `VerdictBanner` (GO / CAUTION /
BLOCK + confidence), `ScaleCard`, `RiskList`, `LineageList`, `BottleneckList`,
`RecommendationList`. All read-only output.

### Honest limitations (in the spec)

- Offline (catalog-only) estimates are deliberately **conservative**; tightening them
  with a live `EXPLAIN` plan is out of scope here (this surface stays offline).
- The Observatory-fed catalog's table mapping is best-effort; bundled schemas are the
  reliable default.
- Inspector never executes SQL and never connects to a database.

---

## Components summary

| Component | Responsibility | Location (tracked) |
|---|---|---|
| JSON writer + `num_rows` | `CatalogResult` (+row totals, provenance) → `catalog.json` | `psdl_observatory/catalog_writers.py`, `catalog.py` |
| CLI `--json` | emit `catalog.json` | `psdl_observatory/cli.py` |
| Generation script | DS wrapper, atomic write | `psdl_observatory/scripts/build_catalog.sh` (new) |
| Observatory reader | `/api/observatory/status` + `/catalog` | `backend/app/routers/observatory.py` (new) |
| Preflight router | `/api/preflight/check` + `/catalogs` (offline) | `backend/app/routers/preflight.py` (new) |
| Catalog adapter | `catalog.json` → Preflight `Catalog` | `backend/app/services/observatory_to_preflight.py` (new) |
| Catalog UI | read-only browser | `frontend/src/components/observatory/` (new) |
| Preflight UI | SQL input + report | `frontend/src/components/preflight/` (new) |

## Testing

- **Observatory:** unit-test the JSON writer (contract shape + provenance + `num_rows`);
  `--json` CLI emits a valid file. Follows `psdl_observatory/tests/` patterns.
- **Adapter:** unit-test `catalog.json` → Preflight `Catalog` (row_estimate from
  num_rows; graceful handling of unmappable tables).
- **Backend:** endpoint tests — observatory (configured/missing/stale/malformed) and
  preflight (bundled-catalog check returns a valid report; offline never opens a
  connection; bad SQL degrades gracefully).
- **Frontend:** typecheck + manual. The repo has no FE test framework; none is added.

## Out of scope

- Live database connectors / `EXPLAIN`-based tightened estimates.
- Batch / worklist triage at organizational scale.
- Governed/shared catalog: RBAC, scheduled scans, multi-user, institutional ownership.
- Multi-source `datasetSpec` authoring / table-binding judgement.
- In-app auth, accounts, hosting, persistence (no DB).

## Build order

1. Capability 1: Observatory catalog (writer + `num_rows`, script, backend, browser).
2. Capability 2a: Preflight check with **bundled** catalogs (router + UI).
3. Capability 2b: Observatory→Preflight adapter (real-number checks).
