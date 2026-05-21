"""Tests for vocabulary search reranker rules.

These tests construct synthetic VocabularySearchResult candidates
(no embedding model required) to verify the RuleBasedReranker
orders results correctly for known-problematic queries documented
in GitHub issue #3.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.vocabulary_search.base import VocabularySearchResult  # noqa: E402
from app.services.vocabulary_search.rerankers import RuleBasedReranker  # noqa: E402


def _make(concept_id: int, name: str, raw_score: float = 0.5) -> VocabularySearchResult:
    return VocabularySearchResult(
        concept_id=concept_id,
        concept_name=name,
        raw_score=raw_score,
    )


def _top_name(reranker, query, candidates):
    ranked = reranker.rerank(query, candidates, concepts_data={})
    return ranked[0].concept_name


@pytest.fixture
def reranker():
    return RuleBasedReranker()


def test_heart_rate_prefers_simple_over_invasive(reranker):
    """Issue #3: 'Heart rate Intra arterial line by Invasive' should not rank first."""
    candidates = [
        _make(1, "Heart rate", raw_score=0.50),
        _make(2, "Heart rate Intra arterial line by Invasive", raw_score=0.55),
        _make(3, "Heart rate by Pulse oximetry", raw_score=0.48),
    ]
    assert _top_name(reranker, "heart rate", candidates) == "Heart rate"


def test_hemoglobin_prefers_general_over_venous(reranker):
    """Issue #3: 'Hemoglobin [Mass/volume] in Venous blood' should not rank first
    when the query is the generic 'hemoglobin'."""
    candidates = [
        _make(1, "Hemoglobin [Mass/volume] in Blood", raw_score=0.50),
        _make(2, "Hemoglobin [Mass/volume] in Venous blood", raw_score=0.55),
        _make(3, "Hemoglobin [Mass/volume] in Arterial blood", raw_score=0.52),
    ]
    assert _top_name(reranker, "hemoglobin", candidates) == "Hemoglobin [Mass/volume] in Blood"


def test_blood_pressure_prefers_systolic_over_panel(reranker):
    """Issue #3: 'Blood pressure panel' is acceptable but a single measurement
    is preferable when the user types the generic 'blood pressure'."""
    candidates = [
        _make(1, "Systolic blood pressure", raw_score=0.50),
        _make(2, "Blood pressure panel", raw_score=0.55),
        _make(3, "Diastolic blood pressure", raw_score=0.49),
    ]
    top = _top_name(reranker, "blood pressure", candidates)
    assert top != "Blood pressure panel"
    assert top in {"Systolic blood pressure", "Diastolic blood pressure"}


def test_creatinine_still_picks_serum_plasma(reranker):
    """Regression: existing correct behavior for creatinine must not break."""
    candidates = [
        _make(1, "Creatinine [Mass/volume] in Serum or Plasma", raw_score=0.50),
        _make(2, "Creatinine [Mass/volume] in Urine", raw_score=0.48),
        _make(3, "Creatinine renal clearance", raw_score=0.45),
    ]
    assert (
        _top_name(reranker, "creatinine", candidates)
        == "Creatinine [Mass/volume] in Serum or Plasma"
    )


def test_glucose_still_picks_serum_plasma(reranker):
    """Regression: existing correct behavior for glucose must not break."""
    candidates = [
        _make(1, "Glucose [Mass/volume] in Serum or Plasma", raw_score=0.50),
        _make(2, "Glucose [Mass/volume] in Urine", raw_score=0.48),
        _make(3, "Glucose tolerance 2 hour post challenge", raw_score=0.46),
    ]
    assert (
        _top_name(reranker, "glucose", candidates)
        == "Glucose [Mass/volume] in Serum or Plasma"
    )


def test_panel_penalty_only_applies_to_generic_vital_queries(reranker):
    """A panel concept should NOT be penalized when the user explicitly searches for one."""
    candidates = [
        _make(1, "Basic metabolic panel", raw_score=0.55),
        _make(2, "Sodium [Mass/volume] in Serum or Plasma", raw_score=0.50),
    ]
    assert (
        _top_name(reranker, "basic metabolic panel", candidates)
        == "Basic metabolic panel"
    )


def test_method_device_penalty_only_short_generic_query(reranker):
    """The new method/device penalty should only fire for short generic queries,
    not when the user explicitly asks for the invasive variant."""
    candidates = [
        _make(1, "Heart rate Intra arterial line by Invasive", raw_score=0.90),
        _make(2, "Heart rate", raw_score=0.50),
    ]
    # Long query (>2 tokens) — the new -0.3 method/device penalty should NOT fire.
    # Raw_score gap (0.40) is large enough to survive existing " by " (-0.1) penalty.
    top = _top_name(
        reranker,
        "invasive intra arterial heart rate monitoring",
        candidates,
    )
    assert top == "Heart rate Intra arterial line by Invasive"
