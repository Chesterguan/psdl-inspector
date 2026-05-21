<p align="center">
  <img src="assets/logo.jpeg" alt="PSDL Inspector" width="400">
</p>

<p align="center">
  <a href="https://github.com/Chesterguan/psdl-inspector"><img src="https://img.shields.io/badge/version-0.2.0-blue.svg" alt="Version"></a>
  <a href="https://pypi.org/project/psdl-lang/"><img src="https://img.shields.io/badge/psdl--lang-0.3.1-green.svg" alt="psdl-lang"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-lightgrey.svg" alt="License"></a>
  <a href="https://zread.ai/Chesterguan/psdl-inspector" target="_blank"><img src="https://img.shields.io/badge/Ask_Zread-_.svg?style=flat&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff" alt="zread"/></a>
</p>

# PSDL Inspector

**Governance middleware for clinical scenarios.**

PSDL Inspector validates, visualizes, and certifies [PSDL](https://github.com/Chesterguan/PSDL) scenarios, producing audit-ready bundles for regulatory compliance.

```
┌─────────────────────────────────────────────────────────────┐
│                    PSDL ECOSYSTEM                           │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐ │
│  │  AUTHORING  │ →  │  INSPECTOR  │ →  │    PLATFORM     │ │
│  │  (YAML)     │    │ (Certify)   │    │   (Execute)     │ │
│  └─────────────┘    └─────────────┘    └─────────────────┘ │
│                                                             │
│  psdl-lang          psdl-inspector     (your runtime)      │
└─────────────────────────────────────────────────────────────┘
```

## Compatibility

| Inspector Version | psdl-lang Version | PSDL Spec | Bundle Version | Status |
|-------------------|-------------------|-----------|----------------|--------|
| 0.2.x | 0.3.1 | 0.3 | 1.1 | **Current** |
| 0.1.x | 0.3.1 | 0.3 | 1.0 | Maintained |
| - | 0.2.x | 0.2 | - | Not supported |
| - | < 0.2 | - | - | Not supported |

> **Note**: PSDL Inspector requires psdl-lang 0.3.x. The psdl-lang library provides parsing, validation, and IR generation that Inspector builds upon.

## Features

| Feature | Description |
|---------|-------------|
| **Build** | Visual scenario builder with guided workflow and OMOP vocabulary search |
| **Generate** | AI-assisted scenario creation with OpenAI or local Ollama |
| **Validate** | Real-time syntax and semantic validation via psdl-lang |
| **Visualize** | Interactive DAG view with ReactFlow (signal → trend → logic) |
| **Outline** | Semantic tree navigation of scenario structure |
| **Anchor** | Automatic terminology binding to OMOP vocabulary at export |
| **Bundle** | Generate checksummed certified bundles with terminology anchors |
| **Export** | IRB preparation with AI-enriched Word document export |
| **MEDS Preview** | Synthesize a 10-row MEDS-format Parquet preview from anchored signals, no DB required; ships with `psdl-meds` CLI for offline conversion |

## What Inspector Does NOT Do

Inspector is **governance middleware** — it certifies that algorithms are correct. It does not execute them.

| Out of Scope | Reason |
|--------------|--------|
| Connect to patient data (EHR, OMOP, FHIR) | Execution platform responsibility |
| Execute scenarios in production | Execution platform responsibility |
| Send clinical alerts | Execution platform responsibility |
| Handle PHI/HIPAA data | No patient data in certification |

## Try It Out

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/Chesterguan/psdl-inspector.git
cd psdl-inspector
docker-compose up
```

Open http://localhost:9806

> **Note**: The Docker image includes the full OMOP vocabulary (~1GB) for immediate terminology search. First build may take a few minutes.

**Optional**: Add your API keys for AI generation:
```bash
cp .env.example .env
# Edit .env with OPENAI_API_KEY=sk-...
docker-compose up
```

### Option 2: Deploy Your Own

See [Deployment Guide](docs/DEPLOYMENT.md) for Vercel + Render setup.

---

## Development Setup

### Requirements

- Python 3.9+
- Node.js 18+
- psdl-lang 0.3.1 (installed automatically)

### 1. Clone Repository

```bash
git clone https://github.com/Chesterguan/psdl-inspector.git
cd psdl-inspector
```

### 2. Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8200
```

API available at http://localhost:8200

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

App available at http://localhost:9806

### 4. Configure AI (Optional)

For AI-assisted scenario generation:

```bash
# Option 1: OpenAI (recommended - fast, accurate)
export OPENAI_API_KEY="sk-your-key-here"

# Option 2: Local Ollama (private, no API key needed)
brew install ollama
ollama serve
ollama pull mistral-small
```

### 5. Verify Installation

Navigate to http://localhost:9806. The header should display:
```
Inspector v0.2.0
psdl-lang v0.3.1
```

## Wizard Workflow

PSDL Inspector uses a 3-step wizard workflow:

### Step 1: Input

Three input modes are available:

- **Builder Mode** (New in v0.2.0): Constrained visual builder with guided workflow
  - Signal selection with OMOP vocabulary search
  - Trend configuration with metric selection
  - Logic rule builder with severity levels
  - Outputs configuration (decisions, features, evidence)
  - Audit section (intent, rationale, provenance)

- **Generate Mode**: AI-assisted scenario creation from natural language
  - OpenAI GPT-4o-mini (cloud, recommended)
  - Ollama (local, privacy-preserving)
  - Auto-validation and error correction
  - Optional clinical context for accurate thresholds

- **Editor Mode**: Manual YAML editing with CodeMirror
  - Syntax highlighting and auto-completion
  - Line numbers and template insertion
  - Real-time validation feedback

### Step 2: Preview
- **Outline**: Tree view of signals, trends, and logic with dependency tracking
- **DAG**: Interactive ReactFlow graph visualization
  - Custom node shapes (parallelogram, rounded rect, diamond, hexagon)
  - Severity-based coloring for logic nodes
  - Node details panel on hover
- **Bundle**: Certified audit bundle preview with checksum and governance checklist

### Step 3: Export
- **Governance Documentation**: Clinical summary, justification, risk assessment
- **JSON Bundle**: Checksummed certified audit bundle with terminology anchors
- **Word Document**: AI-enriched IRB documentation with:
  - Executive summary and clinical background
  - Algorithm overview and data elements
  - Safety considerations and limitations
  - Technical appendix

## Architecture

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

## API Reference

### GET /api/version
Returns version information.
```json
{
  "inspector": "0.2.0",
  "psdl_lang": "0.3.1"
}
```

### GET /api/generate/status
Check LLM provider availability.
```json
{
  "openai": { "available": true, "model": "gpt-4o-mini" },
  "ollama": { "available": true, "model": "mistral-small", "models": [...] },
  "default_provider": "openai"
}
```

### POST /api/generate/scenario
Generate PSDL scenario from natural language.
```json
{
  "prompt": "Detect AKI using creatinine changes",
  "provider": "openai",
  "max_retries": 3,
  "clinical_context": "KDIGO criteria..."
}
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
Synthesize a 10-row MEDS preview shard from anchored signals.
```json
// Request
{
  "anchors": [
    {
      "psdl_signal": "serum_creatinine",
      "omop_vocabulary": "LOINC",
      "omop_concept_code": "2160-0",
      "expected_unit": "mg/dL"
    }
  ],
  "n": 10
}

// Response
{
  "n_events": 10,
  "n_subjects": 3,
  "path": "/tmp/psdl_inspector_meds/preview.parquet",
  "codes_used": ["LOINC/2160-0"]
}
```
Subjects are synthetic negative integers and timestamps step by one day from 2024-01-01, so the output can never collide with real PHI. The shard is validated against `meds.schema.data_schema()` before return.

## MEDS Preview (`psdl_meds`)

Inspector embeds the [`psdl_meds`](backend/psdl_meds/) shared library so authors can see what their scenario will produce in [MEDS](https://github.com/Medical-Event-Data-Standard/meds) format **before** running it against any real data. Use the "Preview MEDS shape" card on the Export step, or the `psdl-meds` CLI for offline work:

```bash
# Convert a CSV of (subject_id, time, code, numeric_value) rows to MEDS Parquet
psdl-meds convert --input cohort.csv --out cohort.parquet

# Synthesize a preview shard from anchored signals (no DB needed)
psdl-meds preview --anchors anchors.json --out preview.parquet -n 10
```

The same library is used by [PSDL Workbench](https://github.com/Chesterguan/PSDL-workbench) for live OMOP-backed cohort exports.

## Certified Audit Bundle

Inspector outputs **Certified Audit Bundles** — the contract between authoring and execution:

```json
{
  "bundle_version": "1.1",
  "certified_at": "2026-01-26T10:30:00Z",
  "checksum": "sha256:abc123...",

  "scenario": {
    "name": "AKI_Detection",
    "version": "0.3.1",
    "raw_yaml": "...",
    "parsed": { /* Full IR */ }
  },

  "terminology_anchors": {
    "anchors": {
      "creatinine": {
        "concept_id": 3016723,
        "vocabulary_id": "LOINC",
        "concept_code": "2160-0",
        "concept_name": "Creatinine [Mass/volume] in Serum or Plasma",
        "standard_unit": "mg/dL",
        "match_confidence": "high"
      }
    },
    "unanchored_refs": [],
    "anchored_count": 1,
    "total_refs": 1
  },

  "validation": {
    "psdl_lang_version": "0.3.1",
    "inspector_version": "0.2.0",
    "valid": true,
    "errors": [],
    "warnings": []
  },

  "audit": {
    "intent": "Detect early AKI for timely intervention",
    "rationale": "Based on KDIGO guidelines",
    "provenance": "doi:10.1038/..."
  },

  "summary": "Human-readable summary for IRB..."
}
```

### Terminology Anchors (v1.1)

The `terminology_anchors` section maps semantic refs (e.g., "creatinine") to OMOP concept IDs. This enables:

- **Portable execution**: Same scenario runs on any OMOP-compliant site
- **Interoperability**: Standard vocabulary binding (LOINC, SNOMED, RxNorm)
- **Audit trail**: Clear mapping from algorithm refs to standard concepts

See [EXECUTION_CONTRACT.md](docs/EXECUTION_CONTRACT.md) for how execution platforms use these anchors.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 14, React 18, Tailwind CSS |
| Editor | CodeMirror 6 |
| Visualization | ReactFlow, dagre (auto-layout) |
| Backend | FastAPI, Python 3.9+ |
| Validation | psdl-lang 0.3.1 |
| AI Generation | OpenAI GPT-4o-mini, Ollama |
| Document Export | python-docx |

## Related Projects

| Project | Description | Link |
|---------|-------------|------|
| **PSDL** | Patient Scenario Definition Language spec | [GitHub](https://github.com/Chesterguan/PSDL) |
| **psdl-lang** | Python library for PSDL parsing | [PyPI](https://pypi.org/project/psdl-lang/) |
| **psdl_meds** | MEDS (Medical Event Data Standard) writer + validator, embedded here and reused by Workbench | [backend/psdl_meds/](backend/psdl_meds/) |
| **PSDL Workbench** | Institutional platform for live cohort execution + governance | [GitHub](https://github.com/Chesterguan/PSDL-workbench) |

## Roadmap

- [x] AI-assisted scenario generation (OpenAI + Ollama)
- [x] Interactive DAG visualization with ReactFlow
- [x] AI-enriched IRB Word document export
- [x] Visual scenario builder with guided workflow
- [x] Terminology anchoring (OMOP vocabulary binding)
- [x] Modular vocabulary search (embedders, retrievers, rerankers)
- [x] MEDS preview + `psdl-meds` CLI (shared library with PSDL Workbench)
- [ ] Editable DAG (visual scenario editing)
- [ ] Lint rules (best practices, style checks)
- [ ] Scenario registry with versioning
- [ ] Semantic diff (structural, not text)

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

Quick start:

```bash
# Backend (with hot reload)
cd backend && source .venv/bin/activate
pip install psdl-lang --upgrade  # Always get latest
uvicorn app.main:app --reload --port 8200

# Frontend (with hot reload)
cd frontend && npm run dev
```

### Code Style

- Python: Follow PEP 8, use type hints
- TypeScript: ESLint + Prettier, strict mode
- Commits: [Conventional commits](https://www.conventionalcommits.org/) (feat:, fix:, docs:, etc.)

## License

MIT License - see [LICENSE](LICENSE) for details.

---

*Built for teams who take clinical algorithm governance seriously.*
