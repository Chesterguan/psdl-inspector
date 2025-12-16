"""Audit bundle export service - Inspector's certified bundle generation.

This is an Inspector-specific feature for governance/compliance.
psdl-lang provides the IR, Inspector provides the audit packaging.
"""

from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from typing import Optional
from importlib.metadata import version as pkg_version

from psdl.core.ir import PSDLScenario

from app.models.schemas import (
    CertifiedBundle,
    ScenarioContent,
    ValidationResult,
    ValidationError,
    AuditInfo,
)
from app.services.parser import scenario_to_dict

# Get versions
try:
    PSDL_LANG_VERSION = pkg_version("psdl-lang")
except Exception:
    PSDL_LANG_VERSION = "unknown"

INSPECTOR_VERSION = "0.1.0"
BUNDLE_VERSION = "1.0"


def generate_certified_bundle(
    scenario: PSDLScenario,
    raw_yaml: str,
    format: str = "json",
    intent: Optional[str] = None,
    rationale: Optional[str] = None,
    provenance: Optional[str] = None,
    errors: Optional[list] = None,
    warnings: Optional[list] = None,
) -> CertifiedBundle:
    """Generate a Certified Audit Bundle from psdl-lang's PSDLScenario.

    This is Inspector's core value: packaging scenarios for governance,
    IRB submission, and audit trails.

    Args:
        scenario: Parsed PSDLScenario from psdl-lang
        raw_yaml: Original YAML content (for checksum and storage)
        format: Export format (json or markdown) - affects summary formatting
        intent: Optional audit intent description
        rationale: Optional clinical rationale
        provenance: Optional source reference (DOI, guideline)
        errors: Validation errors (empty if valid)
        warnings: Validation warnings

    Returns:
        CertifiedBundle with full audit trail
    """
    # Generate checksum from raw YAML (not parsed, for integrity)
    checksum = hashlib.sha256(raw_yaml.encode('utf-8')).hexdigest()

    # Convert psdl-lang IR to dict for serialization
    parsed_dict = scenario_to_dict(scenario)

    # Build scenario content
    scenario_content = ScenarioContent(
        name=scenario.name,
        version=scenario.version,
        raw_yaml=raw_yaml,
        parsed=parsed_dict,
    )

    # Build validation result
    validation = ValidationResult(
        psdl_lang_version=PSDL_LANG_VERSION,
        inspector_version=INSPECTOR_VERSION,
        valid=len(errors or []) == 0,
        errors=[ValidationError(**e) if isinstance(e, dict) else e for e in (errors or [])],
        warnings=[ValidationError(**w) if isinstance(w, dict) else w for w in (warnings or [])],
    )

    # Build audit info (from request or extracted from scenario)
    audit = AuditInfo(
        intent=intent or _extract_audit_field(scenario, 'intent'),
        rationale=rationale or _extract_audit_field(scenario, 'rationale'),
        provenance=provenance or _extract_audit_field(scenario, 'provenance'),
    )

    # Generate human-readable summary
    summary = _generate_summary(scenario, format)

    return CertifiedBundle(
        bundle_version=BUNDLE_VERSION,
        certified_at=datetime.now(timezone.utc).isoformat(),
        checksum=f"sha256:{checksum}",
        scenario=scenario_content,
        validation=validation,
        audit=audit,
        summary=summary,
    )


def _extract_audit_field(scenario: PSDLScenario, field: str) -> Optional[str]:
    """Extract audit field from scenario if psdl-lang supports it.

    Future: psdl-lang may add audit block support.
    """
    # Check if scenario has audit block (future psdl-lang feature)
    if hasattr(scenario, 'audit') and scenario.audit:
        return getattr(scenario.audit, field, None)
    return None


def _generate_summary(scenario: PSDLScenario, format: str) -> str:
    """Generate a human-readable summary of the scenario.

    This is Inspector's contribution - making scenarios readable
    for non-technical stakeholders (IRB, admins, auditors).
    """
    lines = []

    # Header
    if format == "markdown":
        lines.append(f"# {scenario.name}")
        if scenario.version:
            lines.append(f"**Version:** {scenario.version}")
        lines.append("")
        if scenario.description:
            lines.append(f"**Description:** {scenario.description}")
            lines.append("")
    else:
        lines.append(f"SCENARIO: {scenario.name}")
        if scenario.version:
            lines.append(f"Version: {scenario.version}")
        if scenario.description:
            lines.append(f"Description: {scenario.description}")
        lines.append("=" * 60)

    # Signals
    if scenario.signals:
        lines.append("")
        if format == "markdown":
            lines.append("## Signals")
            lines.append("")
            lines.append("| Name | Source | Unit | Domain |")
            lines.append("|------|--------|------|--------|")
            for name, sig in scenario.signals.items():
                source = sig.ref or "-"
                unit = sig.unit or "-"
                domain = sig.domain.value if sig.domain else "-"
                lines.append(f"| {name} | {source} | {unit} | {domain} |")
        else:
            lines.append("SIGNALS:")
            for name, sig in scenario.signals.items():
                unit_str = f" ({sig.unit})" if sig.unit else ""
                lines.append(f"  - {name}: ref={sig.ref}{unit_str}")

    # Trends
    if scenario.trends:
        lines.append("")
        if format == "markdown":
            lines.append("## Trends")
            lines.append("")
            for name, trend in scenario.trends.items():
                lines.append(f"**{name}**")
                lines.append(f"- Expression: `{trend.raw_expr}`")
                if trend.description:
                    lines.append(f"- Description: {trend.description}")
                lines.append("")
        else:
            lines.append("TRENDS:")
            for name, trend in scenario.trends.items():
                desc_str = f" -- {trend.description}" if trend.description else ""
                lines.append(f"  - {name}: {trend.raw_expr}{desc_str}")

    # Logic
    if scenario.logic:
        lines.append("")
        if format == "markdown":
            lines.append("## Logic Rules")
            lines.append("")
            for name, logic in scenario.logic.items():
                severity = logic.severity.value.upper() if logic.severity else "INFO"
                lines.append(f"**{name}** [{severity}]")
                lines.append(f"- Condition: `{logic.expr}`")
                if logic.description:
                    lines.append(f"- Description: {logic.description}")
                lines.append("")
        else:
            lines.append("LOGIC RULES:")
            for name, logic in scenario.logic.items():
                severity_str = f" [{logic.severity.value.upper()}]" if logic.severity else ""
                desc_str = f" -- {logic.description}" if logic.description else ""
                lines.append(f"  - {name}{severity_str}: {logic.expr}{desc_str}")

    # Population (if defined)
    if scenario.population:
        lines.append("")
        if format == "markdown":
            lines.append("## Population Filters")
            lines.append("")
            if scenario.population.include:
                lines.append("**Include:**")
                for criterion in scenario.population.include:
                    lines.append(f"- {criterion}")
            if scenario.population.exclude:
                lines.append("")
                lines.append("**Exclude:**")
                for criterion in scenario.population.exclude:
                    lines.append(f"- {criterion}")
        else:
            lines.append("POPULATION FILTERS:")
            if scenario.population.include:
                lines.append("  Include:")
                for criterion in scenario.population.include:
                    lines.append(f"    - {criterion}")
            if scenario.population.exclude:
                lines.append("  Exclude:")
                for criterion in scenario.population.exclude:
                    lines.append(f"    - {criterion}")

    return "\n".join(lines)


# Backward compatibility alias
def generate_audit_bundle(scenario: PSDLScenario, format: str = "json") -> CertifiedBundle:
    """Legacy function - use generate_certified_bundle instead."""
    # This won't have raw_yaml, so we'll generate a placeholder
    from app.services.parser import scenario_to_dict
    import json
    raw_yaml = f"# Reconstructed from parsed scenario\n# Name: {scenario.name}\n"
    return generate_certified_bundle(scenario, raw_yaml, format)
