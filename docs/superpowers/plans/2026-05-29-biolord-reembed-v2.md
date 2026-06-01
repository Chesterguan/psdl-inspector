# BioLORD Re-embed V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-embed the full 563,138-concept vocabulary (`vocab-data-v2`) using BioLORD-2023, publish the pre-built index as a GitHub Release asset (`vocab-embeddings-v2-biolord`), add a self-contained index loader to `psdl_vocab_search`, add a `SearchEngineConfig.biolord_v2()` factory preset, and replace the two live semantic-search router endpoints that still call `SemanticVocabularyService` (OpenAI, SQLite-based) with the modular `VocabularySearchEngine` backed by BioLORD + `RuleBasedReranker`.

**Architecture:**
- Offline build script (`backend/scripts/build_biolord_embeddings.py`) runs on Mac MPS in ~47-78 min, writes embeddings in resumable chunks keyed by concept_id.
- Artifact tarball `vocab-embeddings-v2-biolord.tar.gz` contains four files: `embeddings.npy`, `index.faiss`, `index.faiss.meta`, `metadata.json`. Published to GitHub Release `vocab-embeddings-v2-biolord` on `Chesterguan/psdl-inspector`.
- New `psdl_vocab_search/_index_loader.py` mirrors `psdl_vocab/_data_loader.py` (env override → cache hit → download). Cache at `~/.cache/psdl_vocab_search/v2-biolord/`.
- `SearchEngineConfig.biolord_v2()` factory preset wires `BioLORDEmbedder` + `FAISSRetriever` (pre-loaded from downloaded index) + `RuleBasedReranker`.
- Router replacement: `/api/vocabulary/semantic/search` and `/api/vocabulary/population/search` swap from `get_semantic_vocabulary_service()` to `get_vocabulary_search_engine(SearchEngineConfig.biolord_v2())`.

**Tech Stack:** Python 3.9+, sentence-transformers (`FremyCompany/BioLORD-2023`), FAISS (IndexFlatIP), numpy, FastAPI, PyTorch MPS (Mac) / CPU fallback, GitHub CLI (`gh`).

**Spec reference:** `docs/superpowers/specs/2026-05-21-embedder-comparison.md`

---

## Scope

**In scope:**
- Build script for BioLORD embeddings (resumable, MPS-accelerated)
- Compute + pack the four-file artifact tarball
- GitHub Release publish (tag `vocab-embeddings-v2-biolord`)
- `psdl_vocab_search/_index_loader.py` — env override / cache / download loader
- `SearchEngineConfig.biolord_v2()` factory preset + lazy singleton wiring
- Router swap: replace `SemanticVocabularyService` calls in two endpoints
- Smoke test: "creatinine" → concept 3016723 in top-3
- Full `psdl_vocab_search` test suite passes

**Out of scope:**
- Retraining or fine-tuning BioLORD
- Changing the `RuleBasedReranker` rules (no new rules in this plan)
- EmbeddingGemma evaluation (tracked separately in embedder-comparison open items)
- Workbench adoption (Task #57, separate plan)
- Removing the old `vocabulary_sqlite.py` service (keep for `/vocabulary/search` text path)

---

## File Structure

| File | Action | Description |
|------|--------|-------------|
| `backend/scripts/build_biolord_embeddings.py` | Create | Offline build script — embed + pack artifact |
| `backend/psdl_vocab_search/_index_loader.py` | Create | Download / cache / env-override loader for pre-built index |
| `backend/psdl_vocab_search/factory.py` | Edit | Add `biolord_v2()` preset + lazy singleton wiring via loader |
| `backend/psdl_vocab_search/retrievers.py` | Edit | Add `PreloadedFAISSRetriever` (accepts pre-loaded index, no rebuild) |
| `backend/app/routers/vocabulary.py` | Edit | Swap two endpoints from `SemanticVocabularyService` to `VocabularySearchEngine` |
| `backend/psdl_vocab_search/tests/test_biolord_v2.py` | Create | Smoke + integration tests for BioLORD v2 path |

---

## Task 1 — Build script: embed 563k concepts with BioLORD, write resumable chunks, pack tarball

**Files:**
- Create: `backend/scripts/build_biolord_embeddings.py`

### Input text format (pinned in `metadata.json`)

For each concept, the embedding input is:
```
concept_name | synonym_1 | synonym_2 | ... | search_term_1 | ... | abbrev_1 | ...
```
Rules: all fields lowercased and stripped; `None` values dropped; duplicates removed (ordered by first appearance); joined with ` | `; truncated to 256 characters.

- [ ] **Step 1: Write failing test for `build_concept_text`** at `backend/psdl_vocab_search/tests/test_biolord_v2.py`

```python
"""Tests for BioLORD v2 index loader and factory preset."""
import pytest


def test_build_concept_text_basic():
    from build_biolord_embeddings import build_concept_text
    concept = {
        "concept_name": "  Creatinine [Mass/volume] in Serum or Plasma  ",
        "synonyms": ["Creatinine, Blood", None, "Creatinine, Blood"],
        "search_terms": ["Serum Creatinine"],
        "abbreviations": ["Crea", "CR"],
    }
    text = build_concept_text(concept)
    assert text.startswith("creatinine [mass/volume] in serum or plasma")
    assert "none" not in text
    assert len(text) <= 256
    assert text.count("creatinine, blood") == 1


def test_build_concept_text_no_extras():
    from build_biolord_embeddings import build_concept_text
    concept = {"concept_name": "Heart rate", "synonyms": None, "search_terms": None, "abbreviations": None}
    text = build_concept_text(concept)
    assert text == "heart rate"


def test_build_concept_text_truncation():
    from build_biolord_embeddings import build_concept_text
    long_synonym = "x" * 300
    concept = {"concept_name": "Test", "synonyms": [long_synonym], "search_terms": [], "abbreviations": []}
    text = build_concept_text(concept)
    assert len(text) <= 256
```

Run:
```bash
cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate
PYTHONPATH=scripts pytest psdl_vocab_search/tests/test_biolord_v2.py::test_build_concept_text_basic -x 2>&1 | tail -5
```
Expected: `ModuleNotFoundError: No module named 'build_biolord_embeddings'`.

- [ ] **Step 2: Create `backend/scripts/build_biolord_embeddings.py`** (full source — see the implementation listed in the operator handoff section below; the writing-plans skill embeds it inline here, or refer to the canonical version under git history)

The script does:
- `build_concept_text(concept)` — produces the canonical input text per the format above.
- `_load_model()` — loads `FremyCompany/BioLORD-2023` with MPS → CUDA → CPU fallback.
- `build_index(concepts, out_dir, batch_size)` — resumable per-batch checkpoint to `progress.npz`; final FAISS `IndexFlatIP` (768-dim normalized vectors); writes `embeddings.npy`, `index.faiss`, `index.faiss.meta` (pickle of `list[int]` concept_ids in row order), `metadata.json` (model, dim, num_concepts, text_format, text_rules, built_date, vocab_source).
- `pack_tarball(out_dir)` — packs all four files into `vocab-embeddings-v2-biolord.tar.gz`.
- `main()` — argparse `--vocab`, `--out`, `--batch-size` (default 256). Defaults the vocab path to `~/.cache/psdl_vocab/v2/vocabulary_final.json`.

- [ ] **Step 3: Run text-builder tests — expect pass**

```bash
PYTHONPATH=scripts pytest psdl_vocab_search/tests/test_biolord_v2.py -v -k build_concept_text 2>&1 | tail -10
```
Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
cd /Volumes/extraSupply/Projects/psdl-inspector
git add backend/scripts/build_biolord_embeddings.py backend/psdl_vocab_search/tests/test_biolord_v2.py
git commit -m "feat(vocab): add BioLORD v2 build script + concept_text tests"
```

---

## Task 2 — Operator compute: run the build script, verify tarball

> **Human-gated step** — the agent cannot run a 47-78 min MPS job. Execute manually, then continue.

- [ ] **Step 1: Install deps + run the build (resumable; re-running picks up the checkpoint)**

```bash
cd /Volumes/extraSupply/Projects/psdl-inspector/backend && source .venv/bin/activate
pip install sentence-transformers faiss-cpu torch --quiet
time python scripts/build_biolord_embeddings.py \
    --vocab ~/.cache/psdl_vocab/v2/vocabulary_final.json \
    --out /tmp/biolord_build \
    --batch-size 256
```
Expected: `[build] BioLORD-2023 loaded on mps` → progress bar to 100% → `Final matrix: (563138, 768)` → `Packed /tmp/biolord_build/vocab-embeddings-v2-biolord.tar.gz`.

- [ ] **Step 2: Verify artifact integrity**

```bash
tar -tzf /tmp/biolord_build/vocab-embeddings-v2-biolord.tar.gz
python3 -c "
import json, numpy as np
emb = np.load('/tmp/biolord_build/embeddings.npy')
print('shape:', emb.shape, 'dtype:', emb.dtype)
meta = json.load(open('/tmp/biolord_build/metadata.json'))
print('model:', meta['model'], 'concepts:', meta['num_concepts'])
norms = np.linalg.norm(emb[:100], axis=1)
print('norm range:', norms.min(), '-', norms.max())  # ~1.0
"
```
Expected: `(563138, 768)`, model = `FremyCompany/BioLORD-2023`, norms ~1.0.

---

## Task 3 — Publish GitHub Release asset

> **Human-gated step** — requires GitHub credentials.

- [ ] **Step 1: Create the release**

```bash
gh release create vocab-embeddings-v2-biolord \
    --repo Chesterguan/psdl-inspector \
    --title "BioLORD v2 Embeddings (563k concepts)" \
    --notes "Pre-built FAISS IndexFlatIP embeddings for vocab-data-v2 using FremyCompany/BioLORD-2023. 768-dim, normalized. Text format: concept_name | synonyms | search_terms | abbreviations (lowercased, stripped, deduped, capped 256)." \
    /tmp/biolord_build/vocab-embeddings-v2-biolord.tar.gz
```

- [ ] **Step 2: Record the asset URL** (used in `_index_loader.py`)

```bash
gh release view vocab-embeddings-v2-biolord --repo Chesterguan/psdl-inspector --json assets --jq '.assets[].browserDownloadUrl'
```
Expect: `https://github.com/Chesterguan/psdl-inspector/releases/download/vocab-embeddings-v2-biolord/vocab-embeddings-v2-biolord.tar.gz`

---

## Task 4 — `_index_loader.py`: env override / cache / download

**Files:**
- Create: `backend/psdl_vocab_search/_index_loader.py`

- [ ] **Step 1: Write failing tests** — see `tests/test_biolord_v2.py`:

```python
def test_index_loader_env_override(tmp_path, monkeypatch):
    from psdl_vocab_search._index_loader import get_index_dir
    fake_dir = tmp_path / "fake_index"
    fake_dir.mkdir()
    for fname in ("metadata.json", "index.faiss", "index.faiss.meta", "embeddings.npy"):
        (fake_dir / fname).write_bytes(b"sentinel")
    monkeypatch.setenv("PSDL_VOCAB_SEARCH_DATA_DIR", str(fake_dir))
    assert get_index_dir() == fake_dir


def test_index_loader_cache_hit(tmp_path, monkeypatch):
    from psdl_vocab_search._index_loader import get_index_dir
    monkeypatch.delenv("PSDL_VOCAB_SEARCH_DATA_DIR", raising=False)
    monkeypatch.setenv("PSDL_VOCAB_SEARCH_CACHE_DIR", str(tmp_path))
    for fname in ("metadata.json", "index.faiss", "index.faiss.meta", "embeddings.npy"):
        (tmp_path / fname).write_bytes(b"sentinel")
    assert get_index_dir() == tmp_path
```

- [ ] **Step 2: Create the loader** at `backend/psdl_vocab_search/_index_loader.py` mirroring `psdl_vocab/_data_loader.py`:

```python
"""Resolve the directory containing the pre-built BioLORD v2 FAISS index.

Resolution order:
1. PSDL_VOCAB_SEARCH_DATA_DIR env var (offline override)
2. Cache hit at PSDL_VOCAB_SEARCH_CACHE_DIR (default ~/.cache/psdl_vocab_search/v2-biolord/)
3. Download tarball from the pinned GitHub Release, unpack atomically into the cache dir.

Required artifact files: embeddings.npy, index.faiss, index.faiss.meta, metadata.json.
"""
from __future__ import annotations

import os
import shutil
import ssl
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

INDEX_VERSION = "v2-biolord"
INDEX_TARBALL_URL = (
    "https://github.com/Chesterguan/psdl-inspector/releases/download/"
    "vocab-embeddings-v2-biolord/vocab-embeddings-v2-biolord.tar.gz"
)
REQUIRED_FILES = ("embeddings.npy", "index.faiss", "index.faiss.meta", "metadata.json")


def _cache_dir() -> Path:
    override = os.environ.get("PSDL_VOCAB_SEARCH_CACHE_DIR")
    if override:
        return Path(override)
    return Path.home() / ".cache" / "psdl_vocab_search" / INDEX_VERSION


def _all_present(directory: Path) -> bool:
    return all((directory / f).exists() for f in REQUIRED_FILES)


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _download_and_unpack(cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(prefix=".biolord-", suffix=".tar.gz", dir=str(cache_dir))
    os.close(tmp_fd)
    tmp_tarball = Path(tmp_name)
    try:
        print("[psdl_vocab_search] Downloading BioLORD v2 index ...", flush=True)
        with urllib.request.urlopen(INDEX_TARBALL_URL, context=_ssl_context()) as resp, open(tmp_tarball, "wb") as out:
            shutil.copyfileobj(resp, out)
        tmp_unpack = cache_dir / ".unpack_tmp"
        if tmp_unpack.exists():
            shutil.rmtree(tmp_unpack)
        tmp_unpack.mkdir()
        with tarfile.open(tmp_tarball, "r:gz") as tf:
            tf.extractall(str(tmp_unpack))
        for fname in REQUIRED_FILES:
            src, dst = tmp_unpack / fname, cache_dir / fname
            if src.exists():
                os.replace(src, dst)
        shutil.rmtree(tmp_unpack, ignore_errors=True)
        print(f"[psdl_vocab_search] Index cached at {cache_dir}", flush=True)
    except (urllib.error.URLError, OSError, EOFError, tarfile.TarError) as exc:
        raise RuntimeError(
            f"psdl_vocab_search could not download the BioLORD v2 index from {INDEX_TARBALL_URL} ({exc}). "
            "For offline installs set PSDL_VOCAB_SEARCH_DATA_DIR to a directory containing the four artifact files."
        ) from exc
    finally:
        try:
            tmp_tarball.unlink(missing_ok=True)
        except OSError:
            pass


def get_index_dir() -> Path:
    override = os.environ.get("PSDL_VOCAB_SEARCH_DATA_DIR")
    if override:
        p = Path(override)
        if not p.is_dir():
            raise RuntimeError(f"PSDL_VOCAB_SEARCH_DATA_DIR={override!r} is not a directory")
        if not _all_present(p):
            missing = [f for f in REQUIRED_FILES if not (p / f).exists()]
            raise RuntimeError(f"PSDL_VOCAB_SEARCH_DATA_DIR={override!r} is missing files: {missing}")
        return p
    cache_dir = _cache_dir()
    if _all_present(cache_dir):
        return cache_dir
    _download_and_unpack(cache_dir)
    return cache_dir
```

- [ ] **Step 3: Run loader tests — expect 2 passed.**
- [ ] **Step 4: Commit:** `git add ... && git commit -m "feat(vocab-search): add _index_loader for BioLORD v2 pre-built index"`

---

## Task 5 — `PreloadedFAISSRetriever` + `SearchEngineConfig.biolord_v2()` factory preset

**Files:**
- Edit: `backend/psdl_vocab_search/retrievers.py` (add `PreloadedFAISSRetriever`, register in `RETRIEVER_REGISTRY` under key `"faiss-preloaded"`)
- Edit: `backend/psdl_vocab_search/factory.py` (add `SearchEngineConfig.biolord_v2()` classmethod + module-level `get_biolord_v2_engine()` singleton accessor)

`PreloadedFAISSRetriever`: subclass of `BaseRetriever` whose `_ensure_loaded()` calls `_index_loader.get_index_dir()` (or accepts an injected `index_dir` for tests), reads `index.faiss` with `faiss.read_index` + `index.faiss.meta` (pickle of `list[int]`). `build_index` is a no-op (pre-built). `search(query_embedding, k)` returns `[(concept_id, score), ...]` mapping FAISS row indices back via the stored concept_ids list. TDD tests:

```python
def test_biolord_v2_config_fields():
    from psdl_vocab_search.factory import SearchEngineConfig
    cfg = SearchEngineConfig.biolord_v2()
    assert cfg.embedder == "biolord"
    assert cfg.retriever == "faiss-preloaded"
    assert cfg.reranker == "rules"


def test_preloaded_faiss_retriever_search(tmp_path):
    import numpy as np, faiss, pickle
    from psdl_vocab_search.retrievers import PreloadedFAISSRetriever
    dim = 4
    emb = np.array([[1.0,0,0,0],[0,1.0,0,0],[0,0,1.0,0]], dtype=np.float32)
    idx = faiss.IndexFlatIP(dim); idx.add(emb)
    faiss.write_index(idx, str(tmp_path/"index.faiss"))
    with open(tmp_path/"index.faiss.meta","wb") as f:
        pickle.dump([100,200,300], f)
    r = PreloadedFAISSRetriever(index_dir=tmp_path)
    res = r.search(np.array([1.0,0,0,0], dtype=np.float32), k=2)
    assert res[0][0] == 100 and res[0][1] > 0.99
```

Commit: `feat(vocab-search): PreloadedFAISSRetriever + SearchEngineConfig.biolord_v2() preset`.

---

## Task 6 — Router replacement: SemanticVocabularyService → VocabularySearchEngine

**Files:**
- Edit: `backend/app/routers/vocabulary.py`

Target endpoints:
- `GET /vocabulary/semantic/search`
- `GET /vocabulary/population/search` (filter results by `vocabulary_id` for `type=conditions` → SNOMED / `type=medications` → RxNorm)

Pattern: try BioLORD via `get_biolord_v2_engine()` first; on any exception (engine error), fall back to the legacy `SemanticVocabularyService` *if available*; else raise. Keep `SemanticVocabularyService` import + the `/vocabulary/population/concept/{concept_id}` + `/vocabulary/population/stats` routes (still used) intact.

Add a test asserting `get_biolord_v2_engine` is importable from the router module after the swap.

Commit: `feat(router): swap /semantic/search + /population/search to BioLORD v2 engine`.

---

## Task 7 — Smoke test: "creatinine" → concept 3016723 in top-3

```python
import pytest

@pytest.mark.integration
def test_creatinine_top3():
    from psdl_vocab_search.factory import get_biolord_v2_engine
    engine = get_biolord_v2_engine()
    results = engine.search("creatinine", limit=3)
    ids = [r.concept_id for r in results]
    assert 3016723 in ids, f"expected 3016723 in top-3, got {[(r.concept_id, r.concept_name) for r in results]}"
```

If this fails, the BioLORD + reranker stack isn't doing what the comparison study claimed — investigate before declaring V2 done.

Commit: `test(vocab-search): add creatinine smoke test (integration, requires index)`.

---

## Task 8 — Integration marker + full suite green

- Register an `integration` marker in `backend/pyproject.toml` under `[tool.pytest.ini_options]`.
- Add `backend/psdl_vocab_search/tests/conftest.py` with a `pytest_collection_modifyitems` hook that skips integration tests unless `PSDL_RUN_INTEGRATION=1` OR the BioLORD cache exists OR `PSDL_VOCAB_SEARCH_DATA_DIR` is set.
- Run `pytest psdl_vocab_search/tests/ -m "not integration" -v` — all green; integration tests skipped with reason.
- Run `PSDL_RUN_INTEGRATION=1 pytest psdl_vocab_search/tests/ -v` — including the creatinine smoke test green.

Commit: `test(vocab-search): integration marker + conftest skip guard for BioLORD tests`.

---

## Self-Review

| Check | Command | Expected |
|---|---|---|
| Unit tests pass | `pytest psdl_vocab_search/tests/ -m "not integration" -v` | All green |
| Integration smoke | `PSDL_RUN_INTEGRATION=1 pytest .../test_creatinine_top3 -v` | 3016723 in top-3 |
| Router imports clean | `python -c "from app.routers.vocabulary import router"` | No ImportError |
| Loader env override | covered in unit tests | green |
| Tarball integrity | check `metadata.json`'s `num_concepts` is 563138 | matches |
| Legacy fallback preserved | `BIOLORD_AVAILABLE=False` path still hits `SemanticVocabularyService` | review router diff |

---

## Execution Handoff

**Subagent-driven (recommended for Tasks 1, 4, 5, 6, 7, 8)** — Tasks 2 + 3 are explicit human gates (operator runs the 47-78 min compute + `gh release create`). The agent implements 1, 4, 5, 6, 7, 8 in order, pauses at Task 2 with a BLOCKERS note, and resumes once the operator confirms the release URL is live.

**Inline (single session)** — same flow, manual gates marked in BLOCKERS.md when Task 2 is reached.

Run the Self-Review checklist before declaring the branch ready for PR.
