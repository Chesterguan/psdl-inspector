"""Tests for the env-gated anchoring engine selector (ANCHORING_ENGINE)."""

from types import SimpleNamespace

from psdl_anchoring import service as svc


def test_selector_defaults_to_vocabulary_search_engine(monkeypatch):
    monkeypatch.delenv("ANCHORING_ENGINE", raising=False)
    sentinel_default = object()
    monkeypatch.setattr(svc, "get_vocabulary_search_engine", lambda: sentinel_default)
    monkeypatch.setattr(svc, "get_biolord_v2_engine", lambda: object())
    assert svc._get_anchoring_engine() is sentinel_default


def test_selector_returns_biolord_when_env_set(monkeypatch):
    monkeypatch.setenv("ANCHORING_ENGINE", "biolord_v2")
    sentinel_biolord = object()
    monkeypatch.setattr(svc, "get_vocabulary_search_engine", lambda: object())
    monkeypatch.setattr(svc, "get_biolord_v2_engine", lambda: sentinel_biolord)
    assert svc._get_anchoring_engine() is sentinel_biolord


def test_selector_unknown_value_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("ANCHORING_ENGINE", "bogus")
    sentinel_default = object()
    monkeypatch.setattr(svc, "get_vocabulary_search_engine", lambda: sentinel_default)
    monkeypatch.setattr(svc, "get_biolord_v2_engine", lambda: object())
    assert svc._get_anchoring_engine() is sentinel_default


def test_modular_search_goes_through_selector(monkeypatch):
    """_anchor_with_modular_search must use the selector, not a hardcoded factory.

    Uses a fake engine (no model load) so this verifies wiring only. Thresholds
    are unchanged: final_score 1.0 -> 'high'.
    """
    service = svc.TerminologyAnchoringService()

    class _Res:
        concept_id = 3016723
        concept_code = "2160-0"
        vocabulary_id = "LOINC"
        concept_name = "Creatinine [Mass/volume] in Serum or Plasma"
        domain_id = "Measurement"
        final_score = 1.0

    fake_engine = SimpleNamespace(
        search=lambda q, limit=5, domain=None: [_Res()],
        get_by_id=lambda cid: {},
    )
    used = {}

    def _select():
        used["called"] = True
        return fake_engine

    monkeypatch.setattr(svc, "_get_anchoring_engine", _select)
    anchor = service._anchor_with_modular_search("creatinine", "creatinine", "Measurement")

    assert used.get("called") is True
    assert anchor.concept_id == 3016723
    assert anchor.match_confidence == "high"
