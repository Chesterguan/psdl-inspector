# PSDL Inspector Backend

FastAPI backend for PSDL Inspector - provides validation, generation, and export APIs.

## Tech Stack

- **FastAPI** - Modern Python web framework
- **psdl-lang** - PSDL parsing and validation
- **httpx** - Async HTTP client for LLM APIs
- **python-docx** - Word document generation
- **Pydantic** - Data validation and serialization

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
│   └── vocabulary.py          # Vocabulary search endpoints
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
```

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

*Updated: 2026-01-26*
