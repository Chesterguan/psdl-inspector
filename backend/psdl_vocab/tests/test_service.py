"""Smoke tests for the psdl_vocab package — loads the bundled OMOP vocab
and exercises search + lookup. Hermetic: no network, no Inspector imports."""

import pytest

from psdl_vocab import VocabularyService, get_vocabulary_service


@pytest.fixture(scope="module")
def vocab():
    vs = VocabularyService()
    vs.load()
    return vs


def test_loads_expected_concept_count(vocab):
    stats = vocab.get_stats()
    # bundled vocabulary_final.json has 76,596 concepts; assert a floor
    # rather than exact so a future vocab rebuild doesn't break this test
    assert stats["total_concepts"] > 70_000


def test_get_by_id_returns_known_concept(vocab):
    # 3016723 = Creatinine [Mass/volume] in Serum or Plasma (LOINC)
    # Verified present in bundled data via probe.
    c = vocab.get_by_id(3016723)
    assert c is not None
    assert "creatinine" in c["concept_name"].lower()
    assert c["vocabulary_id"] == "LOINC"


def test_search_returns_results(vocab):
    results = vocab.search("creatinine", limit=5)
    assert len(results) > 0
    # at least one result should be a creatinine concept
    assert any("creatinine" in r["concept_name"].lower() for r in results)


def test_search_respects_limit(vocab):
    results = vocab.search("glucose", limit=3)
    assert len(results) <= 3


def test_get_vocabulary_service_singleton_loads():
    vs = get_vocabulary_service()
    vs.load()
    assert vs.get_stats()["total_concepts"] > 70_000


def test_get_by_id_missing_returns_none(vocab):
    # a concept_id that cannot exist
    assert vocab.get_by_id(-1) is None
