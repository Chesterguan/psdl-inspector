"""Audit bundle export service - Inspector's certified bundle generation.

This is an Inspector-specific feature for governance/compliance.
psdl-lang provides the IR, Inspector provides the audit packaging.

Key addition: terminologyAnchors - OMOP vocabulary binding that enables
portable execution across different sites with their own datasetSpec.
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
    TerminologyAnchors,
    SignalGroupOutline,
)
from app.services.parser import scenario_to_dict
from app.services.terminology_anchoring import get_terminology_anchoring_service

# Get versions
try:
    PSDL_LANG_VERSION = pkg_version("psdl-lang")
except Exception:
    PSDL_LANG_VERSION = "unknown"

INSPECTOR_VERSION = "0.2.0"
BUNDLE_VERSION = "1.2"  # Added signal_groups (RFC 2026-04-09)


def generate_certified_bundle(
    scenario: PSDLScenario,
    raw_yaml: str,
    format: str = "json",
    intent: Optional[str] = None,
    rationale: Optional[str] = None,
    provenance: Optional[str] = None,
    errors: Optional[list] = None,
    warnings: Optional[list] = None,
    include_terminology_anchors: bool = True,
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
        include_terminology_anchors: Whether to anchor refs to OMOP vocabulary

    Returns:
        CertifiedBundle with full audit trail and terminology anchors
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

    # Generate terminology anchors (OMOP vocabulary binding)
    terminology_anchors: Optional[TerminologyAnchors] = None
    if include_terminology_anchors:
        try:
            anchoring_service = get_terminology_anchoring_service()
            terminology_anchors = anchoring_service.anchor_scenario(scenario)

            # Add warnings for unanchored refs
            if terminology_anchors.unanchored_refs:
                if warnings is None:
                    warnings = []
                for ref in terminology_anchors.unanchored_refs:
                    warnings.append({
                        "message": f"Unanchored terminology ref: '{ref}' - no OMOP concept match found. Sites must provide custom mapping in datasetSpec.",
                        "severity": "warning",
                        "path": f"signals.{ref}",
                    })
        except Exception as e:
            # Don't fail bundle export if anchoring fails
            if warnings is None:
                warnings = []
            warnings.append({
                "message": f"Terminology anchoring failed: {str(e)}. Bundle exported without vocabulary binding.",
                "severity": "warning",
            })

    # Build validation result
    validation = ValidationResult(
        psdl_lang_version=PSDL_LANG_VERSION,
        inspector_version=INSPECTOR_VERSION,
        valid=len(errors or []) == 0,
        errors=[ValidationError(**e) if isinstance(e, dict) else e for e in (errors or [])],
        warnings=[ValidationError(**w) if isinstance(w, dict) else w for w in (warnings or [])],
    )

    # Build audit info (from request, scenario, or raw YAML)
    audit = AuditInfo(
        intent=intent or _extract_audit_field(scenario, 'intent', raw_yaml),
        rationale=rationale or _extract_audit_field(scenario, 'rationale', raw_yaml),
        provenance=provenance or _extract_audit_field(scenario, 'provenance', raw_yaml),
    )

    # Generate human-readable summary
    summary = _generate_summary(scenario, format)

    # Build structured signal groups for the bundle (RFC 2026-04-09)
    signal_groups = _build_signal_group_list(scenario)

    return CertifiedBundle(
        bundle_version=BUNDLE_VERSION,
        certified_at=datetime.now(timezone.utc).isoformat(),
        checksum=f"sha256:{checksum}",
        scenario=scenario_content,
        terminology_anchors=terminology_anchors,
        signal_groups=signal_groups,
        validation=validation,
        audit=audit,
        summary=summary,
    )


def _extract_audit_field(scenario: PSDLScenario, field: str, raw_yaml: Optional[str] = None) -> Optional[str]:
    """Extract audit field from scenario or raw YAML.

    Tries multiple sources:
    1. psdl-lang's parsed audit block (if supported)
    2. Raw YAML parsing as fallback
    """
    # First try psdl-lang's parsed audit block
    if hasattr(scenario, 'audit') and scenario.audit:
        value = getattr(scenario.audit, field, None)
        if value:
            # psdl-lang may return dicts for structured fields like provenance
            if isinstance(value, dict):
                import json
                return json.dumps(value)
            return value

    # Fallback: parse from raw YAML
    if raw_yaml:
        return _extract_audit_from_yaml(raw_yaml, field)

    return None


def _extract_audit_from_yaml(raw_yaml: str, field: str) -> Optional[str]:
    """Extract audit field directly from raw YAML.

    This handles cases where psdl-lang doesn't parse the audit block.
    """
    import yaml
    try:
        parsed = yaml.safe_load(raw_yaml)
        if parsed and isinstance(parsed, dict):
            audit = parsed.get('audit', {})
            if audit and isinstance(audit, dict):
                value = audit.get(field)
                if value:
                    # Remove surrounding quotes if present
                    if isinstance(value, str):
                        return value.strip('"\'')
                    return str(value)
    except Exception:
        pass
    return None


def _build_signal_group_list(scenario: PSDLScenario) -> list:
    """Build structured SignalGroupOutline list from parsed scenario (RFC 2026-04-09)."""
    groups = []
    for name, group in getattr(scenario, 'signal_groups', {}).items():
        groups.append(SignalGroupOutline(
            name=name,
            description=group.description,
            domain=group.domain.value if group.domain else None,
            members=group.members if group.members else [],
        ))
    return groups


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

    # Signal Groups (RFC 2026-04-09)
    if hasattr(scenario, 'signal_groups') and scenario.signal_groups:
        lines.append("")
        if format == "markdown":
            lines.append("## Signal Groups")
            lines.append("")
            for name, group in scenario.signal_groups.items():
                if group.domain:
                    lines.append(f"- **{name}**: domain={group.domain.value} -- {group.description}")
                elif group.members:
                    lines.append(f"- **{name}**: [{', '.join(group.members)}] -- {group.description}")
        else:
            lines.append("SIGNAL GROUPS:")
            for name, group in scenario.signal_groups.items():
                if group.domain:
                    lines.append(f"  - {name}: domain={group.domain.value} -- {group.description}")
                elif group.members:
                    lines.append(f"  - {name}: [{', '.join(group.members)}] -- {group.description}")

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


def _generate_anchors_summary(terminology_anchors: Optional[TerminologyAnchors], format: str) -> str:
    """Generate a summary of terminology anchors for the bundle summary."""
    if not terminology_anchors:
        return ""

    lines = []

    if format == "markdown":
        lines.append("## Terminology Anchors")
        lines.append("")
        lines.append(f"**Anchored**: {terminology_anchors.anchored_count}/{terminology_anchors.total_refs} refs")
        lines.append("")

        if terminology_anchors.anchors:
            lines.append("| Ref | OMOP Concept | Code | Confidence |")
            lines.append("|-----|--------------|------|------------|")
            for ref, anchor in terminology_anchors.anchors.items():
                concept = anchor.concept_name or "-"
                code = f"{anchor.vocabulary_id}:{anchor.concept_code}" if anchor.concept_code else "-"
                lines.append(f"| {ref} | {concept} | {code} | {anchor.match_confidence} |")

        if terminology_anchors.unanchored_refs:
            lines.append("")
            lines.append("**Unanchored refs** (require custom mapping in datasetSpec):")
            for ref in terminology_anchors.unanchored_refs:
                lines.append(f"- {ref}")
    else:
        lines.append("")
        lines.append("TERMINOLOGY ANCHORS:")
        lines.append(f"  Anchored: {terminology_anchors.anchored_count}/{terminology_anchors.total_refs}")

        for ref, anchor in terminology_anchors.anchors.items():
            if anchor.concept_id:
                lines.append(f"  - {ref}: {anchor.concept_name} (ID: {anchor.concept_id}, {anchor.match_confidence})")
            else:
                lines.append(f"  - {ref}: UNANCHORED")

    return "\n".join(lines)


# Backward compatibility alias
def generate_audit_bundle(scenario: PSDLScenario, format: str = "json") -> CertifiedBundle:
    """Legacy function - use generate_certified_bundle instead."""
    # This won't have raw_yaml, so we'll generate a placeholder
    from app.services.parser import scenario_to_dict
    import json
    raw_yaml = f"# Reconstructed from parsed scenario\n# Name: {scenario.name}\n"
    return generate_certified_bundle(scenario, raw_yaml, format)
