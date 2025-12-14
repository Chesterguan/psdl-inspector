# PSDL Inspector

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/Chesterguan/psdl-inspector)
[![psdl-lang](https://img.shields.io/badge/psdl--lang-0.3.x-green.svg)](https://pypi.org/project/psdl-lang/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

**Governance middleware for clinical scenarios.**

PSDL Inspector validates, visualizes, and certifies [PSDL](https://github.com/Chesterguan/PSDL) scenarios, producing audit-ready bundles for regulatory compliance.

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

## Compatibility

| Inspector Version | psdl-lang Version | PSDL Spec | Status |
|-------------------|-------------------|-----------|--------|
| 0.1.x | 0.3.x | 0.3 | **Current** |
| - | 0.2.x | 0.2 | Not supported |
| - | < 0.2 | - | Not supported |

> **Note**: PSDL Inspector requires psdl-lang 0.3.0 or later. The psdl-lang library provides parsing, validation, and IR generation that Inspector builds upon.

## What Inspector Does

| Feature | Description |
|---------|-------------|
| **Validate** | Real-time syntax and semantic validation via psdl-lang |
| **Visualize** | DAG view of signal → trend → logic dependencies |
| **Outline** | Semantic tree navigation of scenario structure |
| **Certify** | Generate checksummed audit bundles |
| **Export** | IRB-ready documentation with human-readable summaries |

## What Inspector Does NOT Do

Inspector is **governance middleware** — it certifies that algorithms are correct. It does not execute them.

| Out of Scope | Reason |
|--------------|--------|
| Connect to patient data (EHR, OMOP, FHIR) | Execution platform responsibility |
| Execute scenarios in production | Execution platform responsibility |
| Send clinical alerts | Execution platform responsibility |
| Handle PHI/HIPAA data | No patient data in certification |

## Quick Start

### Requirements

- Python 3.11+
- Node.js 18+
- psdl-lang 0.3.0+ (installed automatically)

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

### 4. Verify Installation

Navigate to http://localhost:9806. The header should display:
```
Inspector v0.1.0
psdl-lang v0.3.x
```

## Features

### Validation Engine
- Syntax validation (YAML structure)
- Semantic validation (signal/trend/logic references)
- Real-time error highlighting in editor
- Powered by psdl-lang parser

### Semantic Outline
- Tree view of signals, trends, and logic
- Dependency tracking (depends_on / used_by)
- Click to navigate to definitions

### DAG Visualization
- Mermaid.js graph of scenario logic flow
- AND/OR gate visualization
- Signal → Trend → Logic dependency chain

### Audit Bundle Export
- JSON bundle with full metadata
- SHA-256 checksum for integrity verification
- Human-readable summary for IRB review
- Audit fields: intent, rationale, provenance

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
│              │  (PyPI package)     │                     │
│              └─────────────────────┘                     │
└──────────────────────────────────────────────────────────┘
```

## API Reference

### GET /api/version
Returns version information.
```json
{
  "inspector": "0.1.0",
  "psdl_lang": "0.3.0"
}
```

### POST /api/validate
Validate a PSDL scenario.
```json
// Request
{ "content": "scenario: MyScenario\n..." }

// Response
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

### POST /api/outline
Generate semantic outline with dependency tracking.

### POST /api/export/bundle
Export certified audit bundle with checksum.

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

## Tech Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Frontend | Next.js | 14.x |
| UI | React, Tailwind CSS | 18.x, 3.x |
| Editor | CodeMirror | 6.x |
| Backend | FastAPI | 0.100+ |
| Validation | psdl-lang | 0.3.x |
| Visualization | Mermaid.js | 10.x |

## Related Projects

| Project | Description | Link |
|---------|-------------|------|
| **PSDL** | Patient Scenario Definition Language spec | [GitHub](https://github.com/Chesterguan/PSDL) |
| **psdl-lang** | Python library for PSDL parsing | [PyPI](https://pypi.org/project/psdl-lang/) |

## Roadmap

- [ ] Lint rules (best practices, style checks)
- [ ] Scenario registry with versioning
- [ ] Semantic diff (structural, not text)
- [ ] Review workflow with approval states
- [ ] API authentication

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

---

*Built for teams who take clinical algorithm governance seriously.*
