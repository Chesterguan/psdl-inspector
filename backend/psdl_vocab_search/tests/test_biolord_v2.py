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
