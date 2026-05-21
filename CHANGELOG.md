# Changelog

All notable changes to PSDL Inspector will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `psdl_meds` package: MEDS (Medical Event Data Standard) writer, validator,
  preview synthesizer, and `psdl-meds` CLI (convert + preview).
- `POST /api/meds/preview` endpoint and Preview MEDS card on the Export
  step. Generates a 10-row synthetic shard from anchored signals so authors
  can see what their scenario will produce in MEDS format before running
  against real data.
- End-to-end demo walkthrough — [YouTube](https://youtu.be/j-3UHeCyHDk).
  Recording kit (scenarios + cue sheets + DevTools loader) at
  [`docs/demos/`](docs/demos/), with two scenarios shipped: Sepsis-3 qSOFA
  screen (clinical) and T2DM + diabetic nephropathy cohort (research).
- Demo scenarios published as reusable PSDL examples:
  `docs/demos/sepsis-screening/scenario.yaml` and
  `docs/demos/t2d-nephropathy-cohort/scenario.yaml`.

### Fixed
- `MedsPreviewCard` now runs terminology anchoring itself for raw-YAML
  scenarios; previously only Builder-created scenarios (which pre-populate
  `concept_id` on each signal) could generate a MEDS preview.
- `generate_irb_document()` no longer crashes when a logic rule omits
  `severity:` — intermediate building-block rules (e.g. qSOFA components)
  are now exported as `[INFO]` instead of producing a 500.
- Tracking pin for `psdl-lang` bumped to `>=0.4.0`; README compatibility
  table and embedded version examples updated to match.
- Welcome guide modal for first-time users
- Help button in header to reopen guide
- Navigation bar in Preview step with "Continue to Export" button
- Audit fields (intent, rationale, provenance) now extracted from YAML in export bundle
- EXECUTION_CONTRACT.md documentation
- **Docker Deployment**: Full Docker Compose setup with vocabulary included
  - Backend image includes OMOP vocabulary (~1GB) for immediate terminology search
  - Frontend image with Next.js standalone build
  - Works identically to local development
  - `.env.example` for API key configuration
  - Deployment guide for Vercel + Render

### Changed
- Enhanced YAML editor with line numbers, template button, and copy button
- Improved transition animation between wizard steps

### Fixed
- Fixed navigation flow from Preview to Export in all input modes
- Fixed audit section parsing in export bundle generation
- Fixed vocabulary endpoint 503 error handling in Builder mode

## [0.2.0] - 2026-01-26

### Added
- **Terminology Anchoring**: Automatic OMOP vocabulary binding at export time
  - Anchors semantic refs (e.g., "creatinine") to OMOP concept_ids
  - Confidence levels: high, medium, low, unanchored
  - Warnings for unanchored refs
- **Visual Builder**: Constrained PSDL builder with guided workflow
  - Signal selection with OMOP vocabulary search
  - Trend configuration with metric selection
  - Logic rule builder with severity levels
  - Outputs configuration (decisions, features, evidence)
  - Audit section (intent, rationale, provenance)
- **Modular Vocabulary Search**: Pluggable architecture for concept matching
  - Embedders: MiniLM, SapBERT, BioLORD, OpenAI
  - Retrievers: FAISS, NumPy, HNSW
  - Rerankers: Rules, String similarity, Hybrid
- Bundle version upgraded to 1.1 with terminology_anchors

### Changed
- YAML generation aligned 100% with psdl-lang spec
- Logic expressions now reference trends (not signals directly)
- Signals use `unit:` field (not `expected_unit:`)
- Outputs use structured format with `decision:`, `features:`, `evidence:`

## [0.1.0] - 2025-12-17

### Added
- Initial release
- **AI-Assisted Generation**
  - OpenAI GPT-4o-mini integration
  - Local Ollama support (privacy-preserving)
  - Few-shot prompting with PSDL examples
  - Auto-validation with retry (up to 3 attempts)
  - Optional clinical context for accurate thresholds
- **Validation**
  - Real-time syntax validation via psdl-lang
  - Semantic validation with error highlighting
  - Line/column error positioning
- **Visualization**
  - Interactive DAG with ReactFlow
  - Custom node shapes (Signal, Trend, Gate, Logic)
  - Automatic layout with dagre
  - Severity-based coloring
  - Hover details panel
- **Semantic Outline**
  - Tree view of scenario structure
  - Dependency tracking (used_by, depends_on)
- **Export**
  - Certified audit bundle (JSON) with checksum
  - AI-enriched IRB Word document
  - Governance metadata (intent, rationale, provenance)
- **UI/UX**
  - 3-step wizard workflow (Input → Preview → Export)
  - Dark/light theme support
  - CodeMirror YAML editor

### Technical
- Frontend: Next.js 14, React 18, Tailwind CSS
- Backend: FastAPI, Python 3.9+
- Core dependency: psdl-lang 0.3.1

## [0.0.1] - 2025-12-01

### Added
- Project scaffolding
- Basic YAML editor
- Initial psdl-lang integration

---

[Unreleased]: https://github.com/Chesterguan/psdl-inspector/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Chesterguan/psdl-inspector/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Chesterguan/psdl-inspector/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/Chesterguan/psdl-inspector/releases/tag/v0.0.1
