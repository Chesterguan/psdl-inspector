# PSDL Inspector Backend

FastAPI backend for PSDL Inspector - provides validation, generation, and export APIs.

## Tech Stack

- **FastAPI** - Modern Python web framework
- **psdl-lang** - PSDL parsing and validation
- **httpx** - Async HTTP client for LLM APIs
- **python-docx** - Word document generation
- **Pydantic** - Data validation and serialization
- **pyarrow** + **meds** - MEDS Parquet writer/validator (via `psdl_meds`, shipped in-repo)

## Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start development server (port 8200)
uvicorn app.main:app --reload --port 8200

# Run type checking
python -m py_compile app/main.py app/routers/*.py app/services/*.py
```

## Project Structure

```
app/
├── main.py                    # FastAPI application entry
├── models/
│   └── schemas.py             # Pydantic models
├── routers/
│   ├── validate.py            # Validation endpoints
│   ├── outline.py             # Semantic outline endpoints
│   ├── export.py              # Export endpoints
│   ├── generate.py            # AI generation endpoints
│   ├── vocabulary.py          # Vocabulary search endpoints
│   └── meds.py                # MEDS preview endpoint (uses psdl_meds)
└── services/
    ├── parser.py              # psdl-lang wrapper
    ├── validator.py           # Validation logic
    ├── exporter.py            # Certified bundle generation
    ├── docx_exporter.py       # Word document generation
    ├── openai_service.py      # OpenAI GPT integration
    ├── ollama_service.py      # Local Ollama integration
    ├── terminology_anchoring.py  # OMOP vocabulary binding
    ├── vocabulary.py          # Vocabulary lookup service
    └── vocabulary_search/     # Modular semantic search
        ├── base.py            # Abstract interfaces
        ├── embedders.py       # MiniLM, SapBERT, BioLORD, OpenAI
        ├── retrievers.py      # FAISS, NumPy, HNSW
        ├── rerankers.py       # Rules, String similarity, Hybrid
        └── factory.py         # Configuration & factory

psdl_meds/                     # Shared MEDS library (installable, editable)
├── __init__.py                # Public API re-exports
├── codes.py                   # `<VOCAB>/<concept_code>` formatter
├── schema.py                  # MEDS column constants + pyarrow schema
├── writer.py                  # Iterable[dict] → MEDS Parquet shard
├── validator.py               # Cross-checks shard against meds.schema
├── preview.py                 # Synthetic shard from anchored signals
├── cli.py                     # `psdl-meds convert | preview`
├── pyproject.toml             # setuptools build; installable as `psdl-meds`
└── tests/                     # 32 library tests
```

### Installing `psdl_meds`

```bash
# From this repo, editable into the active venv:
pip install -e ./psdl_meds

# Verify
psdl-meds --help
```

PSDL Workbench consumes the same package via `pip install -e ../psdl-inspector/backend/psdl_meds` (PyPI release deferred to Workbench M4).

## Environment Variables

```bash
# OpenAI API (optional - for AI generation)
OPENAI_API_KEY=sk-your-key-here

# Vocabulary Search Configuration (optional)
VOCAB_SEARCH_EMBEDDER=minilm    # minilm, sapbert, biolord, openai
VOCAB_SEARCH_RETRIEVER=faiss    # faiss, numpy, hnsw
VOCAB_SEARCH_RERANKER=rules     # none, rules, string, hybrid
```

Create a `.env` file from the template:
```bash
cp .env.example .env
```

## API Endpoints

### Health & Version
- `GET /` - Health check
- `GET /health` - Health check
- `GET /api/version` - Version info

### Generation (AI)
- `GET /api/generate/status` - Check LLM availability
- `POST /api/generate/scenario` - Generate PSDL from natural language

### Validation
- `POST /api/validate` - Validate PSDL scenario

### Outline
- `POST /api/outline` - Generate semantic outline

### Export
- `POST /api/export/bundle` - Export certified audit bundle
- `POST /api/export/download` - Download bundle as JSON file
- `POST /api/export/draft` - Export draft (even if invalid)
- `POST /api/export/irb-document` - Export Word document for IRB

### MEDS Preview
- `POST /api/meds/preview` - Synthesize a 10-row MEDS Parquet preview from anchored signals (no DB required); response: `{ n_events, n_subjects, path, codes_used }`

## LLM Providers

### OpenAI (Recommended)
- Model: `gpt-4o-mini`
- Fast, accurate, cloud-based
- Requires API key

### Ollama (Local)
- Model: `mistral-small` (default)
- Privacy-preserving, no API key
- Requires local Ollama installation

```bash
# Install Ollama
brew install ollama
ollama serve
ollama pull mistral-small
```

## CORS Configuration

The backend allows requests from the frontend dev server at `http://localhost:9806`.

*Updated: 2026-05-20*
