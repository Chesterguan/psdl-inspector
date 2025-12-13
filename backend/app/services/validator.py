"""PSDL validation service - delegates to psdl-lang.

psdl-lang is the source of truth for validation.
Inspector only wraps the results for API responses.
"""

from __future__ import annotations
from typing import List, Tuple

from psdl.core import parse_scenario as psdl_parse
from psdl.core.ir import PSDLScenario

from app.models.schemas import ValidationError


def validate_scenario(content: str) -> Tuple[PSDLScenario, List[ValidationError], List[ValidationError]]:
    """Validate PSDL scenario using psdl-lang.

    psdl-lang handles all semantic validation:
    - Schema validation
    - Signal reference checking
    - Trend/logic dependency validation
    - Operator validation

    Inspector only formats the results for the API.

    Args:
        content: YAML string content

    Returns:
        Tuple of (parsed_scenario or None, errors, warnings)
    """
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []

    try:
        # psdl-lang does all the heavy lifting
        scenario = psdl_parse(content)

        # Inspector-specific warnings (not validation, just hints)
        # These are UX improvements, not semantic requirements
        warnings.extend(_generate_inspector_hints(scenario))

        return scenario, errors, warnings

    except Exception as e:
        error_msg = str(e)

        # Try to extract structured info from psdl-lang error
        error = ValidationError(
            message=error_msg,
            severity="error",
        )
        errors.append(error)

        return None, errors, warnings


def _generate_inspector_hints(scenario: PSDLScenario) -> List[ValidationError]:
    """Generate Inspector-specific hints (not validation errors).

    These are UX improvements to help users, not semantic requirements.
    psdl-lang defines what's valid; Inspector suggests best practices.
    """
    hints: List[ValidationError] = []

    # Hint: signals defined but not used in any trend
    used_signals = set()
    for trend in scenario.trends.values():
        if trend.signal:
            used_signals.add(trend.signal)

    for sig_name in scenario.signals:
        if sig_name not in used_signals:
            hints.append(ValidationError(
                message=f"Signal '{sig_name}' is defined but not used in any trend",
                severity="warning",
                path=f"/signals/{sig_name}",
            ))

    # Hint: trends defined but not used in logic
    used_trends = set()
    for logic in scenario.logic.values():
        used_trends.update(logic.terms)

    for trend_name in scenario.trends:
        if trend_name not in used_trends:
            hints.append(ValidationError(
                message=f"Trend '{trend_name}' is defined but not used in any logic rule",
                severity="warning",
                path=f"/trends/{trend_name}",
            ))

    return hints
