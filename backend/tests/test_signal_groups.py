"""Tests for signal_groups extension (RFC 2026-04-09)."""
import pytest
from psdl.core.ir import SignalGroup, ClinicalDomain, PSDLScenario, Signal


def test_signal_group_domain_level():
    """Domain-level group has domain set, no members."""
    group = SignalGroup(
        name="all_labs",
        description="All lab results",
        domain=ClinicalDomain.LABORATORY,
    )
    assert group.name == "all_labs"
    assert group.domain == ClinicalDomain.LABORATORY
    assert group.members is None


def test_signal_group_custom():
    """Custom group has members list, no domain."""
    group = SignalGroup(
        name="renal_panel",
        description="Renal monitoring",
        members=["creatinine", "hemoglobin"],
    )
    assert group.name == "renal_panel"
    assert group.domain is None
    assert group.members == ["creatinine", "hemoglobin"]


def test_scenario_signal_groups_default_empty():
    """PSDLScenario.signal_groups defaults to empty dict."""
    scenario = PSDLScenario(
        name="test",
        version="1.0.0",
        description="test",
    )
    assert scenario.signal_groups == {}


def test_scenario_validate_signal_group_valid_members():
    """Validation passes when group members reference defined signals."""
    scenario = PSDLScenario(
        name="test",
        version="1.0.0",
        description="test",
        signals={"creatinine": Signal(name="creatinine", ref="creatinine")},
        signal_groups={
            "renal": SignalGroup(
                name="renal",
                description="Renal panel",
                members=["creatinine"],
            )
        },
    )
    errors = scenario.validate()
    assert not any("signal_group" in e.lower() or "Signal group" in e for e in errors)


def test_scenario_validate_signal_group_invalid_member():
    """Validation fails when group member references unknown signal."""
    scenario = PSDLScenario(
        name="test",
        version="1.0.0",
        description="test",
        signals={"creatinine": Signal(name="creatinine", ref="creatinine")},
        signal_groups={
            "renal": SignalGroup(
                name="renal",
                description="Renal panel",
                members=["creatinine", "nonexistent"],
            )
        },
    )
    errors = scenario.validate()
    assert any("nonexistent" in e for e in errors)


def test_scenario_validate_domain_group_no_member_check():
    """Domain-level groups skip member validation (no members to check)."""
    scenario = PSDLScenario(
        name="test",
        version="1.0.0",
        description="test",
        signal_groups={
            "all_labs": SignalGroup(
                name="all_labs",
                description="All labs",
                domain=ClinicalDomain.LABORATORY,
            )
        },
    )
    errors = scenario.validate()
    assert not any("signal_group" in e.lower() or "Signal group" in e for e in errors)
