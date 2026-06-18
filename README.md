<p align="center">
  <img src="assets/logo.jpeg" alt="PSDL Inspector" width="320">
</p>

<p align="center">
  <a href="https://github.com/Chesterguan/psdl-inspector"><img src="https://img.shields.io/badge/version-0.2.0-blue.svg" alt="Version"></a>
  <a href="https://pypi.org/project/psdl-lang/"><img src="https://img.shields.io/badge/psdl--lang-latest-green.svg" alt="psdl-lang"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-lightgrey.svg" alt="License"></a>
</p>

<h1 align="center">PSDL Inspector</h1>

<p align="center"><b>Describe a clinical cohort or detection rule in one sentence — get back a validated, audit-ready algorithm.</b></p>

PSDL Inspector turns plain English into a **checked clinical scenario**: a visual DAG, OMOP terminology anchoring, a checksummed *certified bundle*, and a real-database **cost preflight** — without writing a line of [PSDL](https://github.com/Chesterguan/PSDL) by hand.

![One sentence → AI-generated, validated PSDL scenario → DAG → certified bundle → live preflight 🟢 GO](assets/aki-preflight-walkthrough.gif)

```bash
git clone https://github.com/Chesterguan/psdl-inspector.git
cd psdl-inspector && docker compose up        # → http://localhost:9806
```

**[▶ 13-second demo](docs/demos/aki-preflight.gif) · [5-minute quickstart](QUICKSTART.md) · [Full walkthrough on YouTube](https://youtu.be/j-3UHeCyHDk)**

- **Describe it, don't code it** — one sentence → a validated PSDL scenario, AI-generated and auto-checked against `psdl-lang`. No new syntax to learn.
- **See the logic** — an interactive DAG + semantic outline surface errors at authoring time, not at IRB review.
- **Hand it off** — a checksummed certified bundle with OMOP anchors + an IRB-ready Word doc, and a SQL preflight that reads **GO / CAUTION / BLOCK** *before* a query ever touches the warehouse.

<!-- Workbench has no public landing page yet; CTA points at email. Swap for a domain address / form when ready. -->
> Inspector is the free, single-user tool. Need a scenario **registry**, role-based review/approval, IRB templates, and SSO across a team? → **PSDL Workbench** *(commercial)* — [request access or info](mailto:chesterfield199512@gmail.com?subject=PSDL%20Workbench%20inquiry).

---

## How it works, in 30 seconds

One clinical sentence becomes a scenario that is generated, validated, and costed against a real **288M-row MIMIC-IV/OMOP** database — the preflight runs a real `EXPLAIN` (metadata only; it never executes the query or reads a patient row):

![sentence → scenario → checked → costed on real data](docs/demos/aki-preflight.gif)

```
"Detect and stage acute kidney injury by the KDIGO criteria using serum creatinine."
        ↓  AI generates PSDL          (gpt-4o-mini, auto-retried until valid)
        ↓  validates                  (real thresholds, real KDIGO stages)
        ↓  anchors to OMOP            (creatinine → LOINC 2160-0, concept 3016723)
        ↓  certifies                  (checksummed bundle, IRB Word doc)
        ↓  preflights on real data    🟢 GO   (real EXPLAIN, nothing executed)
```

Reproduce it yourself: [`docs/demos/`](docs/demos/) ships the scenario YAMLs, narrator cue sheets, and the recording script.

## Who it's for

| You are… | Inspector gives you… |
|----------|----------------------|
| A **clinical researcher / cohort builder** | A sentence → a checked, shareable algorithm you can hand to a data team — no SQL, no DSL to learn first |
| A **data engineer / informaticist** | A readable DAG + semantic diff of the logic, OMOP anchoring, and a preflight that catches a cartesian-join blow-up before it hits the warehouse |
| An **IRB / compliance reviewer** | A checksummed certified bundle + AI-enriched Word doc with intent, rationale, provenance, and a clear audit boundary |

Where Inspector sits in the chain — it **certifies** algorithms; it never executes them:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────────┐
│  AUTHORING  │ →  │  INSPECTOR  │ →  │    PLATFORM     │
│  (sentence  │    │ (validate + │    │   (execute on   │
│   or YAML)  │    │   certify)  │    │  patient data)  │
└─────────────┘    └─────────────┘    └─────────────────┘
   psdl-lang        psdl-inspector      your runtime / Workbench
```

<details>
<summary><b>What Inspector does NOT do</b> (and why that's the point)</summary>

Inspector is **governance middleware** — it certifies that algorithms are correct. It does not execute them.

| Out of Scope | Reason |
|--------------|--------|
| Read patient data (EHR, OMOP, FHIR rows) | Execution platform responsibility |
| Execute scenarios in production | Execution platform responsibility |
| Send clinical alerts | Execution platform responsibility |
| Handle PHI/HIPAA data | No patient data in certification |

Preflight's **optional** live plan connects to *your own local* database for an `EXPLAIN` only — it reads query-plan metadata (estimated rows, scan types), never patient rows. No data is fetched and no query is executed.
</details>

## Try it

**Docker (recommended):**

```bash
git clone https://github.com/Chesterguan/psdl-inspector.git
cd psdl-inspector && docker compose up        # → http://localhost:9806
```

The image bundles the full OMOP vocabulary (~1GB) for terminology search, so the first build takes a few minutes. **AI generation** needs a key (optional):

```bash
cp .env.example .env        # set OPENAI_API_KEY=sk-...
docker compose up
```

No key? Use a local model instead — `brew install ollama && ollama serve && ollama pull mistral-small`. Full local (non-Docker) setup is in the [5-minute quickstart](QUICKSTART.md); self-hosting is in the [Deployment Guide](docs/DEPLOYMENT.md).

<details>
<summary><b>Terminology anchoring engine</b> — BioLORD (default) vs legacy</summary>

OMOP anchoring (and vocab search) can run on two engines, set via `ANCHORING_ENGINE` in `docker-compose.yml`:

- **`biolord_v2` (default)** — highest quality (BioLORD-2023 embeddings + clinical reranker). The embedder is baked into the image; a ~1.7GB concept index downloads **once** on the first anchor and is cached in the `vocab_cache` Docker volume (first anchor ~100s, instant after). Best for accuracy.
- **`` (empty) → legacy** — lighter and offline (no 1.7GB download), but lower-quality matches (no domain reranking). Set `ANCHORING_ENGINE=` to use it.

Either way, the cold cost is one-time; subsequent anchors are instant.
</details>

## Features

| Feature | Description |
|---------|-------------|
| **Generate** | One sentence → a validated scenario, via OpenAI or local Ollama, auto-retried until it passes |
| **Build** | Visual scenario builder with guided workflow and OMOP vocabulary search |
| **Validate** | Real-time syntax and semantic validation via psdl-lang |
| **Visualize** | Interactive DAG view (signal → trend → logic) + semantic outline tree |
| **Anchor** | Automatic terminology binding to OMOP vocabulary at export |
| **Bundle** | Checksummed certified bundles with terminology anchors |
| **Export** | IRB preparation with AI-enriched Word document export |
| **MEDS Preview** | Synthesize a 10-row MEDS-format Parquet preview from anchored signals, no DB required |
| **Data Catalog** | Read-only browse of an Observatory-scanned data lake (schemas, columns, inferred roles) with provenance + staleness |
| **Preflight** | SQL cost/risk check (GO / CAUTION / BLOCK) *before* a query touches the warehouse — offline by default; optional real `EXPLAIN` against your own local DB |

## More demos

▶ **[Sepsis-3 qSOFA walkthrough on YouTube](https://youtu.be/j-3UHeCyHDk)** — a full pipeline run (Builder/YAML → Validate → Outline → DAG → Anchor → Certified Bundle → IRB Word export → MEDS Preview).

[![PSDL Inspector — Sepsis-3 qSOFA walkthrough on YouTube](https://img.youtube.com/vi/j-3UHeCyHDk/hqdefault.jpg)](https://youtu.be/j-3UHeCyHDk "Watch on YouTube")

Two reproducible scenarios ship under [`docs/demos/`](docs/demos/) with scenario YAMLs, narrator cue sheets, and a DevTools loader:

| # | Scenario | Audience |
|---|----------|----------|
| 1 | Sepsis-3 qSOFA + lactate screen | Clinical informatics |
| 2 | T2DM + diabetic nephropathy on metformin cohort | Research / cohort builders |

---

<details>
<summary><b>Wizard workflow</b> (Input → Preview → Export → Prepare)</summary>

### Step 1: Input — three modes
- **Generate** — natural language → scenario (OpenAI GPT-4o-mini cloud, or Ollama local), auto-validation and error correction, optional clinical context for accurate thresholds.
- **Builder** — constrained visual builder: signal selection with OMOP search, trend config, logic rules with severity, outputs, and the audit section (intent, rationale, provenance).
- **Editor** — manual YAML with CodeMirror: syntax highlighting, auto-completion, line numbers, template insertion, real-time validation.

### Step 2: Preview
- **Outline** — tree of signals, trends, and logic with dependency tracking.
- **DAG** — interactive ReactFlow graph: custom node shapes, severity-based coloring, hover detail panel.
- **Bundle** — certified audit bundle preview with checksum and governance checklist.

### Step 3: Export
- **Governance Documentation** — clinical summary, justification, risk assessment.
- **JSON Bundle** — checksummed certified audit bundle with terminology anchors.
- **Word Document** — AI-enriched IRB doc: executive summary, clinical background, algorithm overview, data elements, safety considerations, limitations, technical appendix.

### Step 4: Prepare
- **Data Catalog** — browse an Observatory-scanned data lake (read-only).
- **Preflight** — offline or live-DB SQL cost/risk check before extraction.
</details>

<details>
<summary><b>Architecture</b></summary>

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
│  │ Generate │→ │ Editor   │→ │ Preview  │→ │    Export     │   │
│  │ (AI)     │  │ (YAML)   │  │ DAG/Tree │  │ Bundle + Word │   │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API
┌────────────────────────────▼────────────────────────────────────┐
│                     Backend (FastAPI)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ /generate    │  │ /validate    │  │ /export/bundle     │    │
│  │ /outline     │  │              │  │ /export/irb-doc    │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
│         │                 │                    │                │
│  ┌──────▼──────┐  ┌───────▼───────┐  ┌────────▼─────────┐      │
│  │  OpenAI /   │  │   psdl-lang   │  │   python-docx    │      │
│  │   Ollama    │  │  (validation) │  │  (Word export)   │      │
│  └─────────────┘  └───────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 14, React 18, Tailwind CSS |
| Editor | CodeMirror 6 |
| Visualization | ReactFlow, dagre (auto-layout) |
| Backend | FastAPI, Python 3.9+ |
| Validation | psdl-lang (latest) |
| AI Generation | OpenAI GPT-4o-mini, Ollama |
| Document Export | python-docx |
</details>

<details>
<summary><b>API reference</b></summary>

### GET /api/version
```json
{ "inspector": "0.2.0", "psdl_lang": "0.4.0" }
```

### GET /api/generate/status
Check LLM provider availability.

### POST /api/generate/scenario
```json
{ "prompt": "Detect AKI using creatinine changes", "provider": "openai", "max_retries": 3, "clinical_context": "KDIGO criteria..." }
```

### POST /api/validate
Validate a PSDL scenario.

### POST /api/outline
Generate semantic outline with dependency tracking.

### POST /api/export/bundle
Export certified audit bundle with checksum.

### POST /api/export/irb-document
Export AI-enriched Word document for IRB preparation.

### POST /api/meds/preview
Synthesize a 10-row MEDS preview shard from anchored signals. Subjects are synthetic negative integers and timestamps step from 2024-01-01, so the output can never collide with real PHI; the shard is validated against `meds.schema.data_schema()` before return.
</details>

<details>
<summary><b>Certified audit bundle</b> (the authoring → execution contract)</summary>

```json
{
  "bundle_version": "1.2",
  "certified_at": "2026-01-26T10:30:00Z",
  "checksum": "sha256:abc123...",
  "scenario": { "name": "AKI_Detection", "version": "0.3.1", "raw_yaml": "...", "parsed": { } },
  "terminology_anchors": {
    "anchors": {
      "creatinine": {
        "concept_id": 3016723, "vocabulary_id": "LOINC", "concept_code": "2160-0",
        "concept_name": "Creatinine [Mass/volume] in Serum or Plasma",
        "standard_unit": "mg/dL", "match_confidence": "high"
      }
    },
    "unanchored_refs": [], "anchored_count": 1, "total_refs": 1
  },
  "validation": { "psdl_lang_version": "0.4.0", "inspector_version": "0.2.0", "valid": true, "errors": [], "warnings": [] },
  "audit": { "intent": "Detect early AKI for timely intervention", "rationale": "Based on KDIGO guidelines", "provenance": "doi:10.1038/..." },
  "summary": "Human-readable summary for IRB..."
}
```

The `terminology_anchors` section maps semantic refs (e.g., "creatinine") to OMOP concept IDs, enabling portable execution across any OMOP-compliant site, standard vocabulary binding (LOINC, SNOMED, RxNorm), and a clear audit trail. See [EXECUTION_CONTRACT.md](docs/EXECUTION_CONTRACT.md) for how execution platforms consume it.

### MEDS Preview (`psdl_meds`)

Inspector embeds the [`psdl_meds`](backend/psdl_meds/) library so authors can see what their scenario produces in [MEDS](https://github.com/Medical-Event-Data-Standard/meds) format **before** running it against real data — the "Preview MEDS shape" card on Export, or the CLI:

```bash
psdl-meds convert --input cohort.csv --out cohort.parquet
psdl-meds preview --anchors anchors.json --out preview.parquet -n 10
```

The same library backs **PSDL Workbench** for live OMOP-backed cohort exports.
</details>

<details>
<summary><b>Compatibility</b></summary>

Inspector **always tracks the latest `psdl-lang`** — the requirements pin is `psdl-lang>=0.4.0`. The table records the spec/bundle versions consumed at each Inspector release; older Inspector versions are not retroactively bumped.

| Inspector Version | psdl-lang at release | PSDL Spec | Bundle Version | Status |
|-------------------|----------------------|-----------|----------------|--------|
| 0.2.x | 0.4.x (latest) | 0.4 | 1.1 | **Current** |
| 0.1.x | 0.3.1 | 0.3 | 1.0 | Maintained (legacy spec) |
| - | < 0.2 | - | - | Not supported |
</details>

## Related projects

| Project | Description | Link |
|---------|-------------|------|
| **PSDL** | Patient Scenario Definition Language spec | [GitHub](https://github.com/Chesterguan/PSDL) |
| **psdl-lang** | Python library for PSDL parsing | [PyPI](https://pypi.org/project/psdl-lang/) |
| **psdl_meds** | MEDS writer + validator, embedded here and reused by Workbench | [backend/psdl_meds/](backend/psdl_meds/) |
| **PSDL Workbench** | Institutional platform for live cohort execution + governance | Commercial (closed-source / SaaS) |

## Roadmap

- [x] AI-assisted scenario generation (OpenAI + Ollama)
- [x] Interactive DAG visualization with ReactFlow
- [x] AI-enriched IRB Word document export
- [x] Visual scenario builder with guided workflow
- [x] Terminology anchoring (OMOP vocabulary binding)
- [x] MEDS preview + `psdl-meds` CLI (shared library with PSDL Workbench)
- [ ] Editable DAG (visual scenario editing)
- [ ] Lint rules (best practices, style checks)
- [ ] Scenario registry with versioning
- [ ] Semantic diff (structural, not text)

## Contributing

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Python: PEP 8 + type hints. TypeScript: ESLint + Prettier, strict mode. Commits: [Conventional Commits](https://www.conventionalcommits.org/).

## License

MIT — see [LICENSE](LICENSE).

---

*Built for teams who take clinical algorithm governance seriously.*
