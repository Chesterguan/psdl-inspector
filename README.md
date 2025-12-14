# PSDL Inspector

**Governance middleware for clinical scenarios.**

PSDL Inspector validates, visualizes, and certifies [PSDL](https://github.com/Chesterguan/PSDL) (Patient Scenario Definition Language) scenarios, producing audit-ready bundles for regulatory compliance.

```
┌─────────────────────────────────────────────────────────────┐
│                    PSDL ECOSYSTEM                            │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │  AUTHORING  │ →  │  INSPECTOR  │ →  │    PLATFORM     │  │
│  │  (YAML)     │    │ (Certify)   │    │   (Execute)     │  │
│  └─────────────┘    └─────────────┘    └─────────────────┘  │
│                                                              │
│  psdl-lang          psdl-inspector     (your runtime)       │
└─────────────────────────────────────────────────────────────┘
```

## What Inspector Does

| Feature | Description |
|---------|-------------|
| **Validate** | Real-time syntax and semantic validation via psdl-lang |
| **Visualize** | DAG view of signal → trend → logic dependencies |
| **Outline** | Semantic tree navigation of scenario structure |
| **Certify** | Generate checksummed audit bundles |
| **Export** | IRB-ready documentation with human-readable summaries |

## What Inspector Does NOT Do

- ❌ Connect to patient data (EHR, OMOP, FHIR)
- ❌ Execute scenarios in production
- ❌ Send clinical alerts
- ❌ Run in HIPAA-sensitive environments

Inspector is **governance middleware** — it certifies that algorithms are correct. Execution platforms consume certified bundles to run algorithms safely.

## Screenshots

*Coming soon*

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+

### 1. Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8200
```

API available at http://localhost:8200

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

App available at http://localhost:9806

### 3. Open in Browser

Navigate to http://localhost:9806 to start inspecting scenarios.

## Features

### Validation Engine
- Syntax validation (YAML parsing)
- Semantic validation (reference checks, type validation)
- Real-time error highlighting in editor

### Semantic Outline
- Tree view of signals, trends, and logic
- Dependency tracking (what uses what)
- Click to navigate to definitions

### DAG Visualization
- Mermaid.js graph of scenario logic flow
- AND/OR gate visualization
- Signal → Trend → Logic dependencies

### Audit Bundle Export
- JSON export with full metadata
- SHA-256 checksum for integrity
- Human-readable summary for IRB review
- Audit trail fields (intent, rationale, provenance)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (Next.js)                     │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌────────────┐  │
│  │ Editor  │→ │ Validate │→ │ Outline│→ │ Export     │  │
│  │ Panel   │  │ Display  │  │ + DAG  │  │ Bundle     │  │
│  └─────────┘  └──────────┘  └────────┘  └────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────┐
│                   Backend (FastAPI)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ /validate   │  │ /outline    │  │ /export/bundle  │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│                         │                                │
│              ┌──────────▼──────────┐                     │
│              │    psdl-lang        │                     │
│              │  (parse, validate)  │                     │
│              └─────────────────────┘                     │
└──────────────────────────────────────────────────────────┘
```

## API Endpoints

### POST /api/validate
Validate a PSDL scenario.

### POST /api/outline
Generate semantic outline with dependencies.

### POST /api/export/bundle
Export certified audit bundle.

### GET /api/version
Get Inspector and psdl-lang versions.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React 18, Tailwind CSS |
| Editor | CodeMirror 6 with YAML syntax |
| Backend | FastAPI, Python 3.11+, Pydantic |
| Validation | psdl-lang (PyPI) |
| Visualization | Mermaid.js |

## Certified Audit Bundle

Inspector outputs **Certified Audit Bundles** — the contract between authoring and execution:

```json
{
  "bundle_version": "1.0",
  "certified_at": "2025-12-14T10:30:00Z",
  "checksum": "sha256:abc123...",

  "scenario": {
    "name": "AKI_Detection",
    "version": "0.3.0",
    "content": "... validated PSDL YAML ..."
  },

  "validation": {
    "psdl_lang_version": "0.3.0",
    "valid": true,
    "errors": [],
    "warnings": []
  },

  "audit": {
    "intent": "Detect early AKI...",
    "rationale": "KDIGO guidelines...",
    "provenance": "doi:10.1038/..."
  },

  "summary": "Human-readable summary for IRB..."
}
```

## Related Projects

- **[PSDL](https://github.com/Chesterguan/PSDL)** — Patient Scenario Definition Language specification
- **[psdl-lang](https://pypi.org/project/psdl-lang/)** — Python library for parsing and validating PSDL

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License

---

*Built for teams who take clinical algorithm governance seriously.*
