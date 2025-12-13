"""Semantic outline generator - Inspector's visualization of psdl-lang IR.

This is an Inspector-specific feature. psdl-lang provides the IR,
Inspector provides the visualization/outline for human consumption.
"""

from __future__ import annotations
from typing import List, Set

from psdl.core.ir import PSDLScenario

from app.models.schemas import (
    OutlineResponse,
    SignalOutline,
    TrendOutline,
    LogicOutline,
)


def generate_outline(scenario: PSDLScenario) -> OutlineResponse:
    """Generate a semantic outline from psdl-lang's PSDLScenario.

    This transforms psdl-lang's IR into a visualization-friendly format
    with dependency tracking for UI rendering.

    Args:
        scenario: Parsed PSDLScenario from psdl-lang

    Returns:
        OutlineResponse with signals, trends, and logic breakdown
    """
    # Build signal outlines
    signals: List[SignalOutline] = []
    for name, sig in scenario.signals.items():
        signal = SignalOutline(
            name=name,
            source=sig.source,
            concept_id=sig.concept_id,
            unit=sig.unit,
            domain=str(sig.domain.value) if sig.domain else None,
            description=None,  # psdl-lang Signal doesn't have description currently
        )
        signals.append(signal)

    # Build trend outlines with dependency tracking
    trends: List[TrendOutline] = []
    for name, trend in scenario.trends.items():
        # Get signal dependency from psdl-lang's parsed trend
        depends_on = [trend.signal] if trend.signal else []

        trend_outline = TrendOutline(
            name=name,
            expr=trend.raw_expr,
            description=trend.description,
            depends_on=depends_on,
        )
        trends.append(trend_outline)

    # Build logic outlines with dependency tracking
    logic_list: List[LogicOutline] = []
    for name, logic in scenario.logic.items():
        # psdl-lang parses the terms (dependencies) for us
        depends_on = list(logic.terms) if logic.terms else []

        # Get operators from psdl-lang (AND, OR, NOT)
        operators = list(logic.operators) if hasattr(logic, 'operators') and logic.operators else []

        logic_outline = LogicOutline(
            name=name,
            expr=logic.expr,
            severity=str(logic.severity.value) if logic.severity else None,
            description=logic.description,
            recommendation=None,  # Future: could add to psdl-lang
            depends_on=depends_on,
            operators=operators,
        )
        logic_list.append(logic_outline)

    # Compute reverse dependencies (used_by)
    _compute_used_by(signals, trends, logic_list)

    return OutlineResponse(
        scenario=scenario.name,
        version=scenario.version,
        description=scenario.description,
        signals=signals,
        trends=trends,
        logic=logic_list,
    )


def _compute_used_by(
    signals: List[SignalOutline],
    trends: List[TrendOutline],
    logic_list: List[LogicOutline],
) -> None:
    """Compute reverse dependency relationships (used_by).

    This is Inspector-specific UX - showing what depends on each element.
    """
    # Signals -> Trends (which trends use each signal)
    signal_map = {s.name: s for s in signals}
    for trend in trends:
        for sig_name in trend.depends_on:
            if sig_name in signal_map:
                signal_map[sig_name].used_by.append(trend.name)

    # Trends -> Logic (which logic rules use each trend)
    trend_map = {t.name: t for t in trends}
    for logic in logic_list:
        for term in logic.depends_on:
            if term in trend_map:
                trend_map[term].used_by.append(logic.name)
