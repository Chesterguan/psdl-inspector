"""Tests for signal_groups extension (RFC 2026-04-09)."""
import pytest
from psdl.core.ir import SignalGroup, ClinicalDomain, PSDLScenario, Signal
from psdl.core.parser import PSDLParser


MINIMAL_YAML = """
scenario: test
version: "1.0.0"
description: "test scenario"

signals:
  creatinine:
    ref: creatinine
    expected_unit: mg/dL
    description: "Serum creatinine"
  hemoglobin:
    ref: hemoglobin
    expected_unit: g/dL
    description: "Hemoglobin"

trends:
  cr_current:
    type: float
    unit: mg/dL
    expr: last(creatinine)
    description: "Current creatinine"
  hgb_current:
    type: float
    unit: g/dL
    expr: last(hemoglobin)
    description: "Current hemoglobin"

logic:
  cr_high:
    when: cr_current >= 4.0
    description: "High creatinine"
"""


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
    assert errors == []


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
    assert errors == []


def test_signal_group_rejects_both_domain_and_members():
    """SignalGroup raises ValueError if both domain and members are set."""
    with pytest.raises(ValueError, match="mutually exclusive"):
        SignalGroup(
            name="bad",
            description="Both set",
            domain=ClinicalDomain.LABORATORY,
            members=["creatinine"],
        )


def test_parse_no_signal_groups():
    """Scenarios without signal_groups parse normally."""
    parser = PSDLParser()
    scenario = parser.parse_string(MINIMAL_YAML)
    assert scenario.signal_groups == {}


def test_parse_domain_level_group():
    """Parse a domain-level signal group."""
    yaml = MINIMAL_YAML + """
signal_groups:
  all_labs:
    domain: laboratory
    description: "All lab results"
"""
    parser = PSDLParser()
    scenario = parser.parse_string(yaml)
    assert "all_labs" in scenario.signal_groups
    group = scenario.signal_groups["all_labs"]
    assert group.domain == ClinicalDomain.LABORATORY
    assert group.members is None
    assert group.description == "All lab results"


def test_parse_custom_group():
    """Parse a custom signal group with members."""
    yaml = MINIMAL_YAML + """
signal_groups:
  renal_panel:
    members: [creatinine, hemoglobin]
    description: "Renal monitoring"
"""
    parser = PSDLParser()
    scenario = parser.parse_string(yaml)
    assert "renal_panel" in scenario.signal_groups
    group = scenario.signal_groups["renal_panel"]
    assert group.domain is None
    assert group.members == ["creatinine", "hemoglobin"]


def test_parse_group_invalid_member_fails_validation():
    """Group referencing unknown signal fails validation."""
    yaml = MINIMAL_YAML + """
signal_groups:
  bad_panel:
    members: [creatinine, nonexistent_signal]
    description: "Bad panel"
"""
    parser = PSDLParser()
    with pytest.raises(Exception, match="nonexistent_signal"):
        parser.parse_string(yaml)


def test_parse_group_missing_description_fails():
    """Group without description raises parse error."""
    yaml = MINIMAL_YAML + """
signal_groups:
  no_desc:
    domain: laboratory
"""
    parser = PSDLParser()
    with pytest.raises(Exception, match="description"):
        parser.parse_string(yaml)


def test_parse_group_domain_and_members_fails():
    """Group with both domain and members raises parse error (Phase 1)."""
    yaml = MINIMAL_YAML + """
signal_groups:
  hybrid:
    domain: laboratory
    members: [creatinine]
    description: "Not allowed in Phase 1"
"""
    parser = PSDLParser()
    with pytest.raises(Exception, match="mutually exclusive"):
        parser.parse_string(yaml)


def test_parse_group_neither_domain_nor_members_fails():
    """Group with neither domain nor members raises parse error."""
    yaml = MINIMAL_YAML + """
signal_groups:
  empty:
    description: "Has neither"
"""
    parser = PSDLParser()
    with pytest.raises(Exception, match="must have either"):
        parser.parse_string(yaml)


def test_parse_group_invalid_domain_fails():
    """Group with invalid domain value raises parse error."""
    yaml = MINIMAL_YAML + """
signal_groups:
  bad_domain:
    domain: not_a_real_domain
    description: "Invalid domain"
"""
    parser = PSDLParser()
    with pytest.raises(Exception, match="unknown domain"):
        parser.parse_string(yaml)


def test_parse_multiple_groups():
    """Parse multiple signal groups of different types."""
    yaml = MINIMAL_YAML + """
signal_groups:
  all_labs:
    domain: laboratory
    description: "All labs"
  renal_panel:
    members: [creatinine, hemoglobin]
    description: "Renal panel"
"""
    parser = PSDLParser()
    scenario = parser.parse_string(yaml)
    assert len(scenario.signal_groups) == 2
    assert "all_labs" in scenario.signal_groups
    assert "renal_panel" in scenario.signal_groups


def test_parse_group_members_not_list_fails():
    """Group with non-list members raises parse error."""
    yaml = MINIMAL_YAML + """
signal_groups:
  bad_type:
    members: creatinine
    description: "Members should be a list"
"""
    parser = PSDLParser()
    with pytest.raises(Exception, match="must be a list"):
        parser.parse_string(yaml)


from app.models.schemas import SignalGroupOutline, OutlineResponse


def test_signal_group_outline_schema():
    """SignalGroupOutline model works for domain-level group."""
    outline = SignalGroupOutline(
        name="all_labs",
        description="All lab results",
        domain="laboratory",
        members=[],
    )
    assert outline.name == "all_labs"
    assert outline.domain == "laboratory"


def test_signal_group_outline_custom():
    """SignalGroupOutline model works for custom group."""
    outline = SignalGroupOutline(
        name="renal_panel",
        description="Renal monitoring",
        members=["creatinine", "hemoglobin"],
    )
    assert outline.members == ["creatinine", "hemoglobin"]
    assert outline.domain is None


def test_outline_response_has_signal_groups_field():
    """OutlineResponse includes signal_groups field defaulting to empty list."""
    # Minimal OutlineResponse with required fields only
    response = OutlineResponse(
        scenario="test",
        version="1.0.0",
        description=None,
        signals=[],
        trends=[],
        logic=[],
    )
    assert response.signal_groups == []


# --- Outliner service tests (RFC 2026-04-09) ---

from app.services.outliner import generate_outline
from app.services.validator import validate_scenario


GROUPS_YAML = MINIMAL_YAML + """
signal_groups:
  all_labs:
    domain: laboratory
    description: "All lab results"
  renal_panel:
    members: [creatinine, hemoglobin]
    description: "Renal monitoring"
"""


def test_outline_includes_signal_groups():
    """Outline response includes signal groups."""
    scenario, errors, warnings = validate_scenario(GROUPS_YAML)
    assert scenario is not None
    outline = generate_outline(scenario)
    assert len(outline.signal_groups) == 2
    names = [g.name for g in outline.signal_groups]
    assert "all_labs" in names
    assert "renal_panel" in names


def test_outline_domain_group_has_domain():
    """Domain-level group outline has domain field set."""
    scenario, errors, warnings = validate_scenario(GROUPS_YAML)
    outline = generate_outline(scenario)
    all_labs = next(g for g in outline.signal_groups if g.name == "all_labs")
    assert all_labs.domain == "laboratory"
    assert all_labs.members == []


def test_outline_custom_group_has_members():
    """Custom group outline has members list."""
    scenario, errors, warnings = validate_scenario(GROUPS_YAML)
    outline = generate_outline(scenario)
    renal = next(g for g in outline.signal_groups if g.name == "renal_panel")
    assert renal.domain is None
    assert renal.members == ["creatinine", "hemoglobin"]


def test_outline_no_groups_when_absent():
    """Outline has empty signal_groups when section not present."""
    scenario, errors, warnings = validate_scenario(MINIMAL_YAML)
    outline = generate_outline(scenario)
    assert outline.signal_groups == []
