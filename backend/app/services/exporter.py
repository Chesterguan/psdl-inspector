"""Audit bundle export service - Inspector's export functionality.

This is an Inspector-specific feature for governance/compliance.
psdl-lang provides the IR, Inspector provides the audit packaging.
"""

from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict

from psdl.core.ir import PSDLScenario

from app.models.schemas import ExportResponse, AuditInfo
from app.services.parser import scenario_to_dict


def generate_audit_bundle(scenario: PSDLScenario, format: str = "json") -> ExportResponse:
    """Generate an audit bundle from psdl-lang's PSDLScenario.

    This is Inspector's value-add: packaging scenarios for governance,
    IRB submission, and audit trails.

    Args:
        scenario: Parsed PSDLScenario from psdl-lang
        format: Export format (json or markdown) - affects summary formatting

    Returns:
        ExportResponse with metadata, scenario, audit info, and summary
    """
    # Convert psdl-lang IR to dict for serialization
    scenario_dict = scenario_to_dict(scenario)

    # Generate metadata
    content_hash = hashlib.sha256(str(scenario_dict).encode()).hexdigest()
    metadata = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "checksum": f"sha256:{content_hash[:16]}",
        "format_version": "1.0",
        "generator": "psdl-inspector",
        "psdl_version": scenario.version,
    }

    # Extract audit info (Inspector adds this structure)
    # Note: psdl-lang may add audit block support in future
    audit = AuditInfo(
        intent=None,  # TODO: extract from scenario if psdl-lang adds audit support
        rationale=None,
        provenance=None,
    )

    # Generate human-readable summary (Inspector's value-add)
    summary = _generate_summary(scenario, format)

    return ExportResponse(
        metadata=metadata,
        scenario=scenario_dict,
        audit=audit,
        summary=summary,
    )


def _generate_summary(scenario: PSDLScenario, format: str) -> str:
    """Generate a human-readable summary of the scenario.

    This is Inspector's contribution - making scenarios readable
    for non-technical stakeholders (IRB, admins, auditors).
    """
    lines = []

    # Header
    if format == "markdown":
        lines.append(f"# {scenario.name} v{scenario.version}")
        lines.append("")
        if scenario.description:
            lines.append(f"**Description:** {scenario.description}")
    else:
        lines.append(f"SCENARIO: {scenario.name} v{scenario.version}")
        if scenario.description:
            lines.append(f"Description: {scenario.description}")
        lines.append("-" * 60)

    # Signals
    lines.append("")
    if format == "markdown":
        lines.append("## Signals")
    else:
        lines.append("SIGNALS")

    for name, sig in scenario.signals.items():
        unit_str = f" ({sig.unit})" if sig.unit else ""
        lines.append(f"  - {name}: source={sig.source}{unit_str}")

    # Trends
    if scenario.trends:
        lines.append("")
        if format == "markdown":
            lines.append("## Trends")
        else:
            lines.append("TRENDS")

        for name, trend in scenario.trends.items():
            desc_str = f" -- {trend.description}" if trend.description else ""
            lines.append(f"  - {name}: {trend.raw_expr}{desc_str}")

    # Logic
    lines.append("")
    if format == "markdown":
        lines.append("## Logic Rules")
    else:
        lines.append("LOGIC RULES")

    for name, logic in scenario.logic.items():
        severity_str = f" [{logic.severity.value.upper()}]" if logic.severity else ""
        desc_str = f" -- {logic.description}" if logic.description else ""
        lines.append(f"  - {name}{severity_str}: {logic.expr}{desc_str}")

    # Population (if defined)
    if scenario.population:
        lines.append("")
        if format == "markdown":
            lines.append("## Population Filters")
        else:
            lines.append("POPULATION FILTERS")

        if scenario.population.include:
            lines.append("  Include:")
            for criterion in scenario.population.include:
                lines.append(f"    - {criterion}")
        if scenario.population.exclude:
            lines.append("  Exclude:")
            for criterion in scenario.population.exclude:
                lines.append(f"    - {criterion}")

    return "\n".join(lines)
