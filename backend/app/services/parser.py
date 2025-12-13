"""PSDL parsing service - delegates to psdl-lang."""

from __future__ import annotations
from typing import Any, Dict, Optional

from psdl.core import parse_scenario as psdl_parse
from psdl.core.ir import PSDLScenario


class ParseError(Exception):
    """Parsing error with optional location info."""

    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column


def parse_scenario(content: str) -> PSDLScenario:
    """Parse PSDL scenario content using psdl-lang.

    Args:
        content: YAML string content

    Returns:
        Parsed PSDLScenario object from psdl-lang

    Raises:
        ParseError: If parsing or validation fails
    """
    try:
        return psdl_parse(content)
    except Exception as e:
        # Extract line number if available from error message
        error_msg = str(e)
        raise ParseError(error_msg) from e


def scenario_to_dict(scenario: PSDLScenario) -> Dict[str, Any]:
    """Convert PSDLScenario to a dictionary for JSON serialization.

    This is an Inspector utility - psdl-lang provides the IR,
    we provide the serialization for API responses.
    """
    result: Dict[str, Any] = {
        "scenario": scenario.name,
        "version": scenario.version,
    }

    if scenario.description:
        result["description"] = scenario.description

    # Signals
    result["signals"] = {}
    for name, sig in scenario.signals.items():
        result["signals"][name] = {
            "source": sig.source,
            "concept_id": sig.concept_id,
            "unit": sig.unit,
            "domain": str(sig.domain.value) if sig.domain else None,
        }

    # Trends
    result["trends"] = {}
    for name, trend in scenario.trends.items():
        result["trends"][name] = {
            "expr": trend.raw_expr,
            "description": trend.description,
        }

    # Logic
    result["logic"] = {}
    for name, logic in scenario.logic.items():
        result["logic"][name] = {
            "expr": logic.expr,
            "severity": str(logic.severity.value) if logic.severity else None,
            "description": logic.description,
        }

    # Population (if present)
    if scenario.population:
        result["population"] = {
            "include": scenario.population.include or [],
            "exclude": scenario.population.exclude or [],
        }

    return result
