# Offline Preflight SQL Check (Plan 2 of 3) Implementation Plan
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax.

**Goal:** Wire the Preflight *offline* core (`run_preflight(sql, catalog, connector=None)`) into Inspector as a read-only "validate-before-run" feature. Backend exposes `POST /api/preflight/check` (runs an offline static analysis of a SQL string against a bundled schema catalog) and `GET /api/preflight/catalogs` (lists selectable bundled catalogs). Frontend adds a `/preflight` view that submits SQL + dialect + catalog and renders the returned `PreflightReport`. Inspector never connects to a database and never executes SQL — `connector=None` is hardcoded.

**Architecture:**
- Inspector calls Preflight's pure offline entry point `run_preflight(sql, catalog, connector=None)`. With `connector=None`, no live query plan is fetched: `query_plan` stays `None`, `confidence` is scored with `has_plan=False`, and the report is built entirely from the static catalog estimate.
- Catalog resolution uses `load_catalog(schema)` against Preflight's *bundled* seed schemas (`omop`, `epic`, `caboodle`, `pcornet`, `clarity`). The Observatory-generated catalog adapter is **Plan 3** and out of scope here.
- Backend router mirrors the two existing Inspector router patterns: `meds.py` (POST + Pydantic request/response models, `HTTPException(400, ...)` for bad input) for `/check`, and `observatory.py` (read-only, env/resource-read per request, never throws, graceful `available`/`reason`) for `/catalogs`.
- Frontend mirrors `app/catalog/page.tsx`: `'use client'`, `API_BASE`, fetch in `useEffect`, graceful loading/unreachable states, presentational components under `components/preflight/` typed from a `types.ts` that mirrors the Pydantic models exactly. `query_plan` is intentionally never rendered (always `null` offline).

**Tech Stack:** FastAPI (Python, backend port 8200), Pydantic v2, `psdl_preflight` (offline core: `sqlglot`, `duckdb`, `pydantic`, `PyYAML`), pytest + FastAPI `TestClient`. Frontend: Next.js 14 App Router + TypeScript + Tailwind (verified with `npx tsc --noEmit`; no JS test framework).

**Spec:** `/Volumes/extraSupply/Projects/psdl-inspector/docs/superpowers/specs/2026-06-03-observatory-catalog-ui-design.md` (Capability 2).

---

## File Structure

| Path | Create/Modify | Responsibility |
|---|---|---|
| `/Volumes/extraSupply/Projects/psdl-inspector/backend/requirements.txt` | Modify | Add the `psdl_preflight` dependency line (recommended PyPI-distribution approach). |
| `/Volumes/extraSupply/Projects/psdl-inspector/backend/app/routers/preflight.py` | Create | Router with `POST /preflight/check` (offline `run_preflight`, `connector=None`) and `GET /preflight/catalogs` (bundled catalog list, graceful). |
| `/Volumes/extraSupply/Projects/psdl-inspector/backend/app/main.py` | Modify | Import `preflight` router and register it with `prefix="/api"`. |
| `/Volumes/extraSupply/Projects/psdl-inspector/backend/tests/test_preflight_router.py` | Create | `TestClient` tests for both endpoints: offline check returns a `PreflightReport` with `query_plan == null`, empty-SQL rejection, unknown-catalog rejection, catalogs list. |
| `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/types.ts` | Create | TS interfaces mirroring the Pydantic models and the three enums. |
| `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/SqlInput.tsx` | Create | SQL textarea + dialect selector + catalog dropdown + Run button. |
| `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/VerdictBanner.tsx` | Create | GO/CAUTION/BLOCK banner from `risk_level` + `confidence` + `runtime_category` badges. |
| `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/ScaleCard.tsx` | Create | `scale` estimate grid + `per_stage` rows. |
| `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/LineageList.tsx` | Create | `lineage.nodes`/`edges`/`filters` as labeled lists. |
| `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/FindingsLists.tsx` | Create | `risk_reasons`, `bottlenecks`, `optimizations` lists, plus a `summary` block (`StudySummary`) and `notes` list. (`summary` is an object, not a list.) Intentionally subsumes the spec's `RiskList`/`BottleneckList`/`RecommendationList` (plus notes/summary) into one component — all `PreflightReport` fields are still rendered; this is a naming/structure deviation only, no functional change. |
| `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/app/preflight/page.tsx` | Create | Page: fetch `/catalogs`, submit `/check`, render report or inline error. |

---

## Task 1 — Add the Preflight offline-core dependency and verify `run_preflight` is importable

Encodes the **recommended dependency approach**: depend on the Preflight offline core published as its own namespaced PyPI distribution (`psdl_preflight`), pinned in `backend/requirements.txt` (the load-bearing runtime/CI file). Live connectors (`psycopg`/`pyodbc`) are a `live` extra Inspector never installs.

**Precondition / blocker:** this plan requires a published `psdl_preflight` wheel reachable from PyPI (or the configured index). If no published release exists yet, publishing `psdl_preflight>=0.1,<0.2` is a blocker that must be resolved before starting this task. The committed `requirements.txt` line stays strictly the pinned PyPI dependency — no user-specific local checkout path is baked into any checked-in file. A developer who has a local editable checkout may install it manually, but that is not encoded in the repo.

**Files:**
- Modify: `/Volumes/extraSupply/Projects/psdl-inspector/backend/requirements.txt`

- [ ] **Write failing test** — verify the offline core is importable in the backend venv. There is no pytest harness for an import check, so use a direct interpreter probe as the failing test. Run:
  ```bash
  cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -c "from preflight import run_preflight; from preflight.contracts import PreflightReport, GeneratedSQL; from preflight.catalog.loader import load_catalog; print('OK')"
  ```
  Expected (failing): `ModuleNotFoundError: No module named 'preflight'`.

- [ ] **Implement** — add the dependency to `requirements.txt`. Append these lines at the end of the file. The offline core's static SQL planning/estimation uses `duckdb`; if `psdl_preflight` does not pull it transitively, pin it explicitly here too (see the duckdb probe below):
  ```
  # psdl_preflight — offline SQL preflight core (run_preflight, connector=None only).
  # Published as the psdl_preflight distribution; import name is `preflight`.
  # Live connectors (psycopg/pyodbc) are the `live` extra and are NOT installed here.
  psdl_preflight>=0.1,<0.2
  # Offline-core runtime dep used for static SQL planning/estimation. psdl_preflight
  # should pull this transitively; pin it explicitly only if it does not.
  duckdb
  ```
  Note: do NOT bake any user-specific local checkout path into `requirements.txt`. If a developer has a local editable checkout, they install it manually (`pip install -e <path-to-psdl_preflight-checkout>`) outside the committed file.

- [ ] **Install + run pass** — install the offline core into the backend venv from the pinned PyPI wheel (a reachable published release is a precondition for this plan; see the blocker note above). A developer with a local editable checkout may instead run `pip install -e <path-to-psdl_preflight-checkout>` manually, but that path is never committed:
  ```bash
  cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && pip install "psdl_preflight>=0.1,<0.2"
  ```
  Then re-run the import probe:
  ```bash
  cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -c "from preflight import run_preflight; from preflight.contracts import PreflightReport, GeneratedSQL; from preflight.catalog.loader import load_catalog; print('OK')"
  ```
  Expected: prints `OK`.

- [ ] **Verify offline call shape (incl. duckdb)** — confirm `duckdb` is importable in the backend venv (the offline core may import it lazily during static planning/estimation, so an import-only probe can pass while a real `/check` fails with `ModuleNotFoundError: No module named 'duckdb'`), then confirm a real offline `run_preflight` call — which exercises the estimation path — returns a `PreflightReport` with `query_plan is None`:
  ```bash
  cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -c "
  import duckdb  # must be importable; offline estimation depends on it
  from preflight import run_preflight
  from preflight.contracts import GeneratedSQL, PreflightReport
  from preflight.catalog.loader import load_catalog
  rep = run_preflight(GeneratedSQL(query='SELECT 1 FROM person', dialect='generic', target='omop'), load_catalog('omop'), connector=None)
  assert isinstance(rep, PreflightReport)
  assert rep.query_plan is None
  print('offline OK', rep.risk_level, rep.confidence, rep.runtime_category)
  "
  ```
  Expected: prints `offline OK <RISK> <CONF> <CAT>` and does not error. If `import duckdb` fails, add the `duckdb` pin to the `requirements.txt` block above and re-install before continuing.

- [ ] **Commit:**
  ```bash
  cd /Volumes/extraSupply/Projects/psdl-inspector && git checkout -b feat/preflight-offline-check && git add backend/requirements.txt && git commit -m "build(preflight): add psdl_preflight offline-core dependency

Pin psdl_preflight>=0.1,<0.2 in the load-bearing requirements.txt. Import
name is \`preflight\`; live connectors (psycopg/pyodbc) stay in the \`live\`
extra and are never installed by Inspector. Verified run_preflight is
importable and returns a PreflightReport with query_plan=None offline.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  ```

---

## Task 2 — Backend `POST /api/preflight/check` + `GET /api/preflight/catalogs`

`/check` mirrors `meds.py` (POST + Pydantic models, `HTTPException(400)` for bad input). `/catalogs` mirrors `observatory.py` (read-only, never throws, graceful list). `connector=None` is hardcoded — never parameterized. Unknown tables are NOT errors (they lower confidence; report still returns `200`); only blank SQL, an unknown catalog name, and `sqlglot` parse failures produce `400`.

**Files:**
- Create: `/Volumes/extraSupply/Projects/psdl-inspector/backend/app/routers/preflight.py`
- Modify: `/Volumes/extraSupply/Projects/psdl-inspector/backend/app/main.py`
- Test: `/Volumes/extraSupply/Projects/psdl-inspector/backend/tests/test_preflight_router.py`

- [ ] **Write failing test** — create `/Volumes/extraSupply/Projects/psdl-inspector/backend/tests/test_preflight_router.py` (mirrors `test_observatory_router.py` / `test_meds_router.py` `TestClient` pattern):
  ```python
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


  def test_check_offline_returns_report_with_null_query_plan():
      body = {
          "sql": "SELECT person_id FROM person",
          "dialect": "generic",
          "catalog_source": "omop",
      }
      resp = client.post("/api/preflight/check", json=body)
      assert resp.status_code == 200, resp.text
      report = resp.json()
      # Offline: query_plan is always null (connector=None, has_plan=False).
      assert report["query_plan"] is None
      # Required top-level fields are present. summary.execution_target echoes
      # the request's catalog_source: run_preflight sets
      # StudySummary.execution_target = sql.target, and the router passes
      # GeneratedSQL(target=req.catalog_source). So this equals "omop" here.
      assert report["summary"]["execution_target"]
      assert report["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
      assert report["confidence"] in ("LOW", "MEDIUM", "HIGH")
      assert report["runtime_category"] in (
          "FAST",
          "MODERATE",
          "HEAVY",
          "EXTREME",
          "UNKNOWN",
      )
      assert isinstance(report["risk_reasons"], list)
      assert isinstance(report["bottlenecks"], list)
      assert isinstance(report["optimizations"], list)
      assert isinstance(report["notes"], list)
      assert "patients" in report["scale"]


  def test_check_rejects_blank_sql():
      resp = client.post(
          "/api/preflight/check",
          json={"sql": "   ", "dialect": "generic", "catalog_source": "omop"},
      )
      assert resp.status_code == 400, resp.text
      assert "sql is required" in resp.json()["detail"]


  def test_check_rejects_unknown_catalog():
      resp = client.post(
          "/api/preflight/check",
          json={
              "sql": "SELECT 1 FROM person",
              "dialect": "generic",
              "catalog_source": "nope_not_real",
          },
      )
      assert resp.status_code == 400, resp.text
      assert "unknown catalog" in resp.json()["detail"]


  def test_check_invokes_run_preflight_offline_with_connector_none(monkeypatch):
      # Spec invariant: offline preflight NEVER opens a connection. The router
      # must call run_preflight with connector=None. Capture the call at the
      # router boundary instead of trusting the downstream package, and prove
      # it is invoked exactly once with connector keyword == None.
      captured = {}
      calls = {"n": 0}

      real_report = client.post(
          "/api/preflight/check",
          json={
              "sql": "SELECT person_id FROM person",
              "dialect": "generic",
              "catalog_source": "omop",
          },
      ).json()

      def fake_run_preflight(generated, catalog, **kwargs):
          calls["n"] += 1
          captured.update(kwargs)
          # Return a previously-captured real report so response validation
          # against PreflightReport still succeeds.
          return preflight_router.PreflightReport(**real_report)

      monkeypatch.setattr(preflight_router, "run_preflight", fake_run_preflight)

      resp = client.post(
          "/api/preflight/check",
          json={
              "sql": "SELECT person_id FROM person",
              "dialect": "generic",
              "catalog_source": "omop",
          },
      )
      assert resp.status_code == 200, resp.text
      assert calls["n"] == 1
      assert "connector" in captured, "run_preflight must be called with an explicit connector kwarg"
      assert captured["connector"] is None  # offline never opens a connection
  ```
  > Note: `PreflightReport` is imported into the router module (`from preflight.contracts import GeneratedSQL, PreflightReport`), so `preflight_router.PreflightReport` and `preflight_router.run_preflight` are both monkeypatchable on `app.routers.preflight`.

- [ ] **Run it (expected fail):**
  ```bash
  cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -m pytest tests/test_preflight_router.py -q
  ```
  Expected: collection/run fails — `ModuleNotFoundError: No module named 'app.routers.preflight'` (router not created / not registered).

- [ ] **Implement the router** — create `/Volumes/extraSupply/Projects/psdl-inspector/backend/app/routers/preflight.py`:
  ```python
  """Offline SQL preflight router.

  Wraps psdl_preflight's pure offline entry point. The connector is hardcoded
  to None: Inspector never connects to a database and never executes SQL. With
  connector=None, run_preflight builds the report entirely from the static
  catalog estimate (query_plan stays None, confidence scored has_plan=False).
  """
  from typing import List

  from fastapi import APIRouter, HTTPException
  from pydantic import BaseModel

  from preflight import run_preflight
  from preflight.contracts import GeneratedSQL, PreflightReport
  from preflight.catalog.loader import load_catalog

  router = APIRouter()

  # Bundled seed schemas shipped with psdl_preflight (catalog/schemas/*.yaml).
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


  @router.get("/preflight/catalogs", response_model=CatalogsResponse)
  def list_catalogs() -> CatalogsResponse:
      # Read-only and never throws. The Observatory adapter that flips
      # observatory_available is Plan 3 / Capability 2b; hardcoded False here.
      return CatalogsResponse(
          bundled=list(BUNDLED_CATALOGS),
          default=DEFAULT_CATALOG,
          observatory_available=False,
      )


  @router.post("/preflight/check", response_model=PreflightReport)
  def check(req: PreflightCheckRequest) -> PreflightReport:
      if not req.sql or not req.sql.strip():
          raise HTTPException(status_code=400, detail="sql is required")

      try:
          catalog = load_catalog(req.catalog_source)
      except FileNotFoundError:
          raise HTTPException(
              status_code=400,
              detail=(
                  f"unknown catalog '{req.catalog_source}'. "
                  f"valid: {', '.join(BUNDLED_CATALOGS)}"
              ),
          )

      # NOTE: confirm against psdl_preflight.contracts.GeneratedSQL whether
      # `target` is the schema/catalog family (omop/epic/...) or a separate
      # execution target. run_preflight sets StudySummary.execution_target =
      # sql.target, so reusing catalog_source here makes the report's
      # execution_target echo the bundled catalog name. If GeneratedSQL.target
      # is meant to be a distinct execution target rather than the catalog
      # family, set it from the intended field instead of catalog_source.
      # (Correctness-only; no offline/OSS-boundary impact — connector stays None.)
      generated = GeneratedSQL(
          query=req.sql,
          dialect=req.dialect,
          target=req.catalog_source,
      )

      try:
          # connector=None => fully OFFLINE. Never parameterized.
          report = run_preflight(generated, catalog, connector=None)
      except Exception as exc:  # noqa: BLE001 - surface parse errors as 400
          raise HTTPException(
              status_code=400, detail=f"SQL parse error: {exc}"
          )

      return report
  ```

- [ ] **Register the router** — edit `/Volumes/extraSupply/Projects/psdl-inspector/backend/app/main.py`. Add `preflight` to the routers import (line 10) and register it after the other `include_router` calls. Change the import line:
  ```python
  from app.routers import validate, outline, export, generate, vocabulary, meds, observatory, preflight
  ```
  and add the registration (after the existing `observatory` include, around line 43):
  ```python
  app.include_router(preflight.router, prefix="/api", tags=["preflight"])
  ```

- [ ] **Run pass:**
  ```bash
  cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -m pytest tests/test_preflight_router.py -q
  ```
  Expected: `5 passed`.

- [ ] **Run the full backend suite (no regressions):**
  ```bash
  cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate && python -m pytest -q -m "not integration"
  ```
  Expected: all collected tests pass (no new failures).

- [ ] **Commit:**
  ```bash
  cd /Volumes/extraSupply/Projects/psdl-inspector && git add backend/app/routers/preflight.py backend/app/main.py backend/tests/test_preflight_router.py && git commit -m "feat(preflight): offline /api/preflight/check + /catalogs

POST /api/preflight/check runs psdl_preflight's run_preflight with
connector=None (fully offline; query_plan always null) against a bundled
catalog and returns the PreflightReport. Blank SQL, unknown catalog, and
sqlglot parse failures return 400; unknown tables are non-fatal and lower
confidence. GET /api/preflight/catalogs lists the bundled schema sources
and degrades gracefully. TestClient tests cover catalogs, the offline check
(query_plan null), blank-SQL and unknown-catalog 400s, and assert run_preflight
is invoked with connector=None so offline never opens a connection.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  ```

---

## Task 3 — Frontend `/preflight` view + components (`tsc --noEmit`)

Mirrors `app/catalog/page.tsx` and the `components/observatory/` presentational pattern: the page fetches and passes data down; components do no fetching. `types.ts` mirrors the Pydantic models and the three enums exactly. `query_plan` is intentionally not rendered (always `null` offline). There is no JS test framework — verification is `npx tsc --noEmit`.

**Files:**
- Create: `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/types.ts`
- Create: `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/SqlInput.tsx`
- Create: `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/VerdictBanner.tsx`
- Create: `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/ScaleCard.tsx`
- Create: `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/LineageList.tsx`
- Create: `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/FindingsLists.tsx`
- Create: `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/app/preflight/page.tsx`

- [ ] **Write failing check** — establish the `tsc --noEmit` gate before any files exist by referencing the not-yet-created modules. Create `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/types.ts` with the model mirror (this is also the first real implementation file, and the import in `page.tsx` will fail to typecheck until every file below exists):
  ```typescript
  export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  export type Confidence = 'LOW' | 'MEDIUM' | 'HIGH';
  export type RuntimeCategory =
    | 'FAST'
    | 'MODERATE'
    | 'HEAVY'
    | 'EXTREME'
    | 'UNKNOWN';

  export interface StudySummary {
    execution_target: string;
    tables: string[];
    domains: string[];
    query_shape: string;
  }

  export interface LineageNode {
    table: string;
    category: string;
    volume: string;
    est_rows: number | null;
  }

  export interface LineageEdge {
    source: string;
    target: string;
    kind: string;
    cardinality_transition: string;
  }

  export interface Lineage {
    nodes: LineageNode[];
    edges: LineageEdge[];
    filters: string[];
  }

  export interface StageEstimate {
    name: string;
    est_rows: number;
  }

  export interface ScaleEstimate {
    patients: number | null;
    encounters: number | null;
    events: number | null;
    intermediate_records: number | null;
    output_records: number | null;
    per_stage: StageEstimate[];
    confidence: Confidence;
  }

  export interface Bottleneck {
    component: string;
    reason: string;
    contribution_pct: number;
  }

  export interface Optimization {
    action: string;
    rationale: string;
    expected_benefit: string;
  }

  export interface PreflightReport {
    summary: StudySummary;
    lineage: Lineage;
    scale: ScaleEstimate;
    risk_level: RiskLevel;
    risk_reasons: string[];
    bottlenecks: Bottleneck[];
    optimizations: Optimization[];
    query_plan: unknown | null;
    runtime_category: RuntimeCategory;
    confidence: Confidence;
    notes: string[];
  }

  export interface CatalogsResponse {
    bundled: string[];
    default: string;
    observatory_available: boolean;
  }
  ```
  Then run the gate (expected fail until the page + components exist):
  ```bash
  cd /Volumes/extraSupply/Projects/psdl-inspector/frontend && npx tsc --noEmit
  ```
  Expected: errors like `Cannot find module './SqlInput'` / `src/app/preflight/page.tsx` not resolving its imports (page not yet created), or no error yet because `page.tsx` is absent — proceed to create the components and page below, after which the gate must pass.

- [ ] **Implement `SqlInput.tsx`** — create `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/SqlInput.tsx`:
  ```typescript
  import { CatalogsResponse } from './types';

  const DIALECTS = ['generic', 'duckdb', 'postgres', 'tsql'];

  interface Props {
    sql: string;
    dialect: string;
    catalogSource: string;
    catalogs: CatalogsResponse | null;
    running: boolean;
    onSqlChange: (v: string) => void;
    onDialectChange: (v: string) => void;
    onCatalogChange: (v: string) => void;
    onRun: () => void;
  }

  export default function SqlInput({
    sql,
    dialect,
    catalogSource,
    catalogs,
    running,
    onSqlChange,
    onDialectChange,
    onCatalogChange,
    onRun,
  }: Props) {
    const bundled = catalogs?.bundled ?? [];
    return (
      <div className="border border-border rounded-md p-4 bg-background-tertiary">
        <textarea
          className="w-full h-40 font-mono text-sm p-2 bg-background text-foreground border border-border rounded"
          placeholder="SELECT person_id FROM person"
          value={sql}
          onChange={(e) => onSqlChange(e.target.value)}
        />
        <div className="flex items-center gap-3 mt-3">
          <label className="text-sm text-muted">
            Dialect
            <select
              className="ml-2 bg-background text-foreground border border-border rounded px-2 py-1"
              value={dialect}
              onChange={(e) => onDialectChange(e.target.value)}
            >
              {DIALECTS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-muted">
            Catalog
            <select
              className="ml-2 bg-background text-foreground border border-border rounded px-2 py-1"
              value={catalogSource}
              onChange={(e) => onCatalogChange(e.target.value)}
            >
              {bundled.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <button
            className="ml-auto bg-accent text-foreground px-4 py-1.5 rounded disabled:opacity-50"
            disabled={running || !sql.trim()}
            onClick={onRun}
          >
            {running ? 'Running…' : 'Run preflight'}
          </button>
        </div>
      </div>
    );
  }
  ```

- [ ] **Implement `VerdictBanner.tsx`** — create `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/VerdictBanner.tsx`:
  ```typescript
  import { Confidence, RiskLevel, RuntimeCategory } from './types';

  interface Props {
    riskLevel: RiskLevel;
    confidence: Confidence;
    runtimeCategory: RuntimeCategory;
  }

  function verdict(risk: RiskLevel): { label: string; cls: string } {
    if (risk === 'LOW') return { label: 'GO', cls: 'bg-green-700 text-white' };
    if (risk === 'MEDIUM')
      return { label: 'CAUTION', cls: 'bg-accent-warning text-black' };
    return { label: 'BLOCK', cls: 'bg-red-700 text-white' };
  }

  export default function VerdictBanner({
    riskLevel,
    confidence,
    runtimeCategory,
  }: Props) {
    const v = verdict(riskLevel);
    return (
      <div className={`rounded-md p-4 flex items-center gap-4 ${v.cls}`}>
        <span className="text-2xl font-bold">{v.label}</span>
        <span className="text-sm opacity-90">risk: {riskLevel}</span>
        <span className="ml-auto text-sm bg-background-tertiary text-foreground px-2 py-0.5 rounded">
          confidence: {confidence}
        </span>
        <span className="text-sm bg-background-tertiary text-foreground px-2 py-0.5 rounded">
          runtime: {runtimeCategory}
        </span>
      </div>
    );
  }
  ```

- [ ] **Implement `ScaleCard.tsx`** — create `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/ScaleCard.tsx`:
  ```typescript
  import { ScaleEstimate } from './types';

  interface Props {
    scale: ScaleEstimate;
  }

  export default function ScaleCard({ scale }: Props) {
    const rows: [string, number | null][] = [
      ['patients', scale.patients],
      ['encounters', scale.encounters],
      ['events', scale.events],
      ['intermediate_records', scale.intermediate_records],
      ['output_records', scale.output_records],
    ];
    const present = rows.filter(([, v]) => v !== null && v !== undefined);
    return (
      <div className="border border-border rounded-md p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-foreground">Scale estimate</h3>
          <span className="text-xs bg-background-tertiary text-muted px-2 py-0.5 rounded">
            confidence: {scale.confidence}
          </span>
        </div>
        {present.length === 0 ? (
          <p className="text-muted text-sm">No scale estimate available.</p>
        ) : (
          <div className="grid grid-cols-2 gap-2 text-sm">
            {present.map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-muted">{k}</span>
                <span className="text-foreground">{v}</span>
              </div>
            ))}
          </div>
        )}
        {scale.per_stage.length > 0 && (
          <div className="mt-3 text-sm">
            <h4 className="text-muted mb-1">Per stage</h4>
            {scale.per_stage.map((s, i) => (
              <div key={i} className="flex justify-between">
                <span className="text-foreground">{s.name}</span>
                <span className="text-muted">{s.est_rows}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }
  ```

- [ ] **Implement `LineageList.tsx`** — create `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/LineageList.tsx`:
  ```typescript
  import { Lineage } from './types';

  interface Props {
    lineage: Lineage;
  }

  export default function LineageList({ lineage }: Props) {
    return (
      <div className="border border-border rounded-md p-4">
        <h3 className="font-semibold text-foreground mb-2">Lineage</h3>
        <h4 className="text-muted text-sm">Nodes</h4>
        {lineage.nodes.length === 0 ? (
          <p className="text-muted text-sm">none</p>
        ) : (
          <ul className="text-sm mb-2">
            {lineage.nodes.map((n, i) => (
              <li key={i} className="text-foreground">
                {n.table} · {n.category} · {n.volume}
                {n.est_rows !== null ? ` · ~${n.est_rows} rows` : ''}
              </li>
            ))}
          </ul>
        )}
        <h4 className="text-muted text-sm">Edges</h4>
        {lineage.edges.length === 0 ? (
          <p className="text-muted text-sm">none</p>
        ) : (
          <ul className="text-sm mb-2">
            {lineage.edges.map((e, i) => (
              <li key={i} className="text-foreground">
                {e.source} → {e.target} ({e.kind})
                {e.cardinality_transition ? ` · ${e.cardinality_transition}` : ''}
              </li>
            ))}
          </ul>
        )}
        <h4 className="text-muted text-sm">Filters</h4>
        {lineage.filters.length === 0 ? (
          <p className="text-muted text-sm">none</p>
        ) : (
          <ul className="text-sm">
            {lineage.filters.map((f, i) => (
              <li key={i} className="text-foreground">
                {f}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }
  ```

- [ ] **Implement `FindingsLists.tsx`** — create `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/components/preflight/FindingsLists.tsx`:
  ```typescript
  import {
    Bottleneck,
    Optimization,
    StudySummary,
  } from './types';

  interface Props {
    summary: StudySummary;
    riskReasons: string[];
    bottlenecks: Bottleneck[];
    optimizations: Optimization[];
    notes: string[];
  }

  export default function FindingsLists({
    summary,
    riskReasons,
    bottlenecks,
    optimizations,
    notes,
  }: Props) {
    return (
      <div className="space-y-4">
        <div className="border border-border rounded-md p-4">
          <h3 className="font-semibold text-foreground mb-2">Risk reasons</h3>
          {riskReasons.length === 0 ? (
            <p className="text-muted text-sm">No risk reasons flagged.</p>
          ) : (
            <ul className="list-disc list-inside text-sm text-foreground">
              {riskReasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="border border-border rounded-md p-4">
          <h3 className="font-semibold text-foreground mb-2">Bottlenecks</h3>
          {bottlenecks.length === 0 ? (
            <p className="text-muted text-sm">none</p>
          ) : (
            <ul className="text-sm text-foreground space-y-1">
              {bottlenecks.map((b, i) => (
                <li key={i}>
                  <span className="font-medium">{b.component}</span> —{' '}
                  {b.reason} ({b.contribution_pct}%)
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="border border-border rounded-md p-4">
          <h3 className="font-semibold text-foreground mb-2">Recommendations</h3>
          {optimizations.length === 0 ? (
            <p className="text-muted text-sm">none</p>
          ) : (
            <ul className="text-sm text-foreground space-y-1">
              {optimizations.map((o, i) => (
                <li key={i}>
                  <span className="font-medium">{o.action}</span> — {o.rationale}
                  {o.expected_benefit ? ` (${o.expected_benefit})` : ''}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="border border-border rounded-md p-4">
          <h3 className="font-semibold text-foreground mb-2">Summary &amp; notes</h3>
          <p className="text-sm text-muted">
            target: {summary.execution_target}
            {summary.query_shape ? ` · shape: ${summary.query_shape}` : ''}
          </p>
          {summary.tables.length > 0 && (
            <p className="text-sm text-muted">
              tables: {summary.tables.join(', ')}
            </p>
          )}
          {summary.domains.length > 0 && (
            <p className="text-sm text-muted">
              domains: {summary.domains.join(', ')}
            </p>
          )}
          {notes.length > 0 && (
            <ul className="list-disc list-inside text-sm text-foreground mt-2">
              {notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    );
  }
  ```

- [ ] **Implement `page.tsx`** — create `/Volumes/extraSupply/Projects/psdl-inspector/frontend/src/app/preflight/page.tsx`:
  ```typescript
  'use client';

  import { useEffect, useState } from 'react';

  import SqlInput from '../../components/preflight/SqlInput';
  import VerdictBanner from '../../components/preflight/VerdictBanner';
  import ScaleCard from '../../components/preflight/ScaleCard';
  import LineageList from '../../components/preflight/LineageList';
  import FindingsLists from '../../components/preflight/FindingsLists';
  import { CatalogsResponse, PreflightReport } from '../../components/preflight/types';

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8200';

  export default function PreflightPage() {
    const [catalogs, setCatalogs] = useState<CatalogsResponse | null>(null);
    const [catalogsError, setCatalogsError] = useState<string | null>(null);
    const [sql, setSql] = useState('');
    const [dialect, setDialect] = useState('generic');
    const [catalogSource, setCatalogSource] = useState('omop');
    const [report, setReport] = useState<PreflightReport | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [running, setRunning] = useState(false);

    useEffect(() => {
      fetch(`${API_BASE}/api/preflight/catalogs`)
        .then((r) => r.json())
        .then((c: CatalogsResponse) => {
          setCatalogs(c);
          setCatalogSource(c.default);
          setCatalogsError(null);
        })
        .catch(() => {
          setCatalogs(null);
          setCatalogsError("Couldn't load catalogs — is the backend running?");
        });
    }, []);

    const run = async () => {
      setRunning(true);
      setError(null);
      setReport(null);
      try {
        const resp = await fetch(`${API_BASE}/api/preflight/check`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sql, dialect, catalog_source: catalogSource }),
        });
        const data = await resp.json();
        if (!resp.ok) {
          setError(data.detail || 'Preflight failed.');
        } else {
          setReport(data as PreflightReport);
        }
      } catch {
        setError("Couldn't reach the backend.");
      } finally {
        setRunning(false);
      }
    };

    return (
      <div className="min-h-screen bg-background text-foreground p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-semibold text-foreground">SQL Preflight</h1>
          <a href="/" className="text-accent text-sm">
            ← Back to Inspector
          </a>
        </div>

        <div className="max-w-4xl mx-auto space-y-4">
          {catalogsError && (
            <div className="border border-accent-warning rounded-md p-3 text-accent-warning text-sm">
              {catalogsError}
            </div>
          )}

          <SqlInput
            sql={sql}
            dialect={dialect}
            catalogSource={catalogSource}
            catalogs={catalogs}
            running={running}
            onSqlChange={setSql}
            onDialectChange={setDialect}
            onCatalogChange={setCatalogSource}
            onRun={run}
          />

          {error && (
            <div className="border border-accent-warning rounded-md p-3 text-accent-warning text-sm">
              {error}
            </div>
          )}

          {report && (
            <>
              <VerdictBanner
                riskLevel={report.risk_level}
                confidence={report.confidence}
                runtimeCategory={report.runtime_category}
              />
              <ScaleCard scale={report.scale} />
              <LineageList lineage={report.lineage} />
              <FindingsLists
                summary={report.summary}
                riskReasons={report.risk_reasons}
                bottlenecks={report.bottlenecks}
                optimizations={report.optimizations}
                notes={report.notes}
              />
            </>
          )}
        </div>
      </div>
    );
  }
  ```

- [ ] **Run pass (`tsc --noEmit`):**
  ```bash
  cd /Volumes/extraSupply/Projects/psdl-inspector/frontend && npx tsc --noEmit
  ```
  Expected: no output, exit code 0 (all `preflight` modules typecheck and resolve).

- [ ] **Commit:**
  ```bash
  cd /Volumes/extraSupply/Projects/psdl-inspector && git add frontend/src/components/preflight frontend/src/app/preflight && git commit -m "feat(preflight): /preflight view + report components

Read-only Next.js page mirroring app/catalog: fetch /api/preflight/catalogs
on mount, POST /api/preflight/check on submit, render the PreflightReport via
presentational components (SqlInput, VerdictBanner, ScaleCard, LineageList,
FindingsLists). types.ts mirrors the Pydantic models/enums exactly. query_plan
is never rendered (always null offline). Verified with npx tsc --noEmit.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  ```

---

## Out of scope

- **Live database connectors / `EXPLAIN`-tightened plans** — `connector` is hardcoded `None`; live plans are out of scope here. The `QueryPlan` subtree is never populated and never rendered.
- **Observatory→Preflight adapter (`observatory_to_preflight.py`) and real-number catalogs** — Plan 3 / Capability 2b. Here `catalog_source` resolves to bundled schema names only; `observatory_available` is hardcoded `false`.
- **Custom catalog directories** (`load_catalog(..., catalog_dir=...)` / `PREFLIGHT_CATALOG_DIR`) — only bundled seed schemas are exposed in this plan.
- **Batch / worklist triage at large scale** — out of scope here.
- **Governance:** RBAC, scheduled scans, multi-user, shared/owned catalogs, in-app auth, accounts, hosting, persistence (no DB).
- **SQL execution of any kind** — Inspector never runs SQL and never opens a connection.
- **Frontend automated test framework** — none exists; verification is `npx tsc --noEmit` only.
