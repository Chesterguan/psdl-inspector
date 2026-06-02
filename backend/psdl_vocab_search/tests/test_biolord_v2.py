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


# ---------------------------------------------------------------------------
# Task 4: _index_loader tests
# ---------------------------------------------------------------------------

def test_index_loader_env_override(tmp_path, monkeypatch):
    from psdl_vocab_search._index_loader import get_index_dir
    fake_dir = tmp_path / "fake_index"
    fake_dir.mkdir()
    for fname in ("metadata.json", "index.faiss", "index.faiss.meta"):
        (fake_dir / fname).write_bytes(b"sentinel")
    monkeypatch.setenv("PSDL_VOCAB_SEARCH_DATA_DIR", str(fake_dir))
    assert get_index_dir() == fake_dir


def test_index_loader_cache_hit(tmp_path, monkeypatch):
    from psdl_vocab_search._index_loader import get_index_dir
    monkeypatch.delenv("PSDL_VOCAB_SEARCH_DATA_DIR", raising=False)
    monkeypatch.setenv("PSDL_VOCAB_SEARCH_CACHE_DIR", str(tmp_path))
    for fname in ("metadata.json", "index.faiss", "index.faiss.meta"):
        (tmp_path / fname).write_bytes(b"sentinel")
    assert get_index_dir() == tmp_path


# ---------------------------------------------------------------------------
# Task 5: PreloadedFAISSRetriever + SearchEngineConfig.biolord_v2() tests
# ---------------------------------------------------------------------------

def test_biolord_v2_config_fields():
    from psdl_vocab_search.factory import SearchEngineConfig
    cfg = SearchEngineConfig.biolord_v2()
    assert cfg.embedder == "biolord"
    assert cfg.retriever == "faiss-preloaded"
    assert cfg.reranker == "rules"


def test_preloaded_faiss_retriever_search(tmp_path):
    import numpy as np
    import faiss
    import pickle
    from psdl_vocab_search.retrievers import PreloadedFAISSRetriever

    dim = 4
    emb = np.array([[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 0]], dtype=np.float32)
    idx = faiss.IndexFlatIP(dim)
    idx.add(emb)
    faiss.write_index(idx, str(tmp_path / "index.faiss"))
    with open(tmp_path / "index.faiss.meta", "wb") as f:
        pickle.dump([100, 200, 300], f)

    r = PreloadedFAISSRetriever(index_dir=tmp_path)
    res = r.search(np.array([1.0, 0, 0, 0], dtype=np.float32), k=2)
    assert res[0][0] == 100 and res[0][1] > 0.99


def test_preloaded_engine_skips_reembed(tmp_path):
    """PreloadedVocabularySearchEngine must not re-embed; it loads the pre-built index."""
    import json
    import numpy as np
    import faiss
    import pickle
    from psdl_vocab_search.factory import PreloadedVocabularySearchEngine
    from psdl_vocab_search.retrievers import PreloadedFAISSRetriever
    from psdl_vocab_search.embedders import get_embedder
    from psdl_vocab_search.rerankers import get_reranker

    # Build a tiny 4-dim index with two concepts.
    dim = 4
    emb = np.array([[1.0, 0, 0, 0], [0, 1.0, 0, 0]], dtype=np.float32)
    idx = faiss.IndexFlatIP(dim)
    idx.add(emb)
    index_dir = tmp_path / "idx"
    index_dir.mkdir()
    faiss.write_index(idx, str(index_dir / "index.faiss"))
    with open(index_dir / "index.faiss.meta", "wb") as f:
        pickle.dump([3016723, 999999], f)

    # Write a minimal vocab JSON.
    vocab_path = tmp_path / "vocab.json"
    vocab_path.write_text(json.dumps([
        {"concept_id": 3016723, "concept_name": "Creatinine [Mass/volume]",
         "concept_code": "2160-0", "vocabulary_id": "LOINC", "domain_id": "Measurement"},
        {"concept_id": 999999, "concept_name": "Glucose [Mass/volume]",
         "concept_code": "2345-7", "vocabulary_id": "LOINC", "domain_id": "Measurement"},
    ]))

    retriever = PreloadedFAISSRetriever(index_dir=index_dir)
    engine = PreloadedVocabularySearchEngine(
        embedder=get_embedder("minilm"),  # will NOT be called during load()
        retriever=retriever,
        reranker=get_reranker("rules"),
        vocab_path=str(vocab_path),
        cache_dir=str(tmp_path / "cache"),
    )
    engine.load()  # should NOT trigger embedding

    assert engine._loaded
    assert 3016723 in engine._concepts_by_id
    assert retriever._loaded  # pre-built index is ready


# ---------------------------------------------------------------------------
# Task 6: router import test
# ---------------------------------------------------------------------------

def test_router_imports_biolord_v2_engine():
    """Verify that get_biolord_v2_engine is importable from the router module."""
    from app.routers.vocabulary import get_biolord_v2_engine  # noqa: F401


# ---------------------------------------------------------------------------
# Task 7: integration smoke test
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_creatinine_top3():
    from psdl_vocab_search.factory import get_biolord_v2_engine
    engine = get_biolord_v2_engine()
    results = engine.search("creatinine", limit=3)
    ids = [r.concept_id for r in results]
    assert 3016723 in ids, (
        f"expected 3016723 in top-3, got {[(r.concept_id, r.concept_name) for r in results]}"
    )
