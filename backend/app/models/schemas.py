"""Pydantic models for API schemas."""

from __future__ import annotations
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field


# --- Validation Models ---


class ValidationError(BaseModel):
    """A validation error or warning."""

    line: Optional[int] = Field(None, description="Line number (1-indexed)")
    column: Optional[int] = Field(None, description="Column number (1-indexed)")
    message: str = Field(..., description="Error message")
    severity: str = Field("error", description="error or warning")
    path: Optional[str] = Field(None, description="JSON path to the error location")


class ValidationRequest(BaseModel):
    """Request to validate a PSDL scenario."""

    content: str = Field(..., description="PSDL scenario content (YAML)")


class ValidationResponse(BaseModel):
    """Response from validation endpoint."""

    valid: bool = Field(..., description="Whether the scenario is valid")
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationError] = Field(default_factory=list)
    parsed: Optional[Dict[str, Any]] = Field(None, description="Parsed scenario if valid")


# --- Outline Models ---


class SignalOutline(BaseModel):
    """Signal definition in the outline."""

    name: str
    source: Optional[str] = None
    concept_id: Optional[int] = None
    unit: Optional[str] = None
    domain: Optional[str] = None
    description: Optional[str] = None
    used_by: List[str] = Field(default_factory=list, description="Trends that use this signal")


class TrendOutline(BaseModel):
    """Trend definition in the outline."""

    name: str
    expr: str
    description: Optional[str] = None
    depends_on: List[str] = Field(default_factory=list, description="Signals this trend uses")
    used_by: List[str] = Field(default_factory=list, description="Logic rules that use this trend")


class LogicOutline(BaseModel):
    """Logic rule in the outline."""

    name: str
    expr: str
    severity: Optional[str] = None
    description: Optional[str] = None
    recommendation: Optional[str] = None
    depends_on: List[str] = Field(
        default_factory=list, description="Trends/logic this rule depends on"
    )
    operators: List[str] = Field(
        default_factory=list, description="Boolean operators (AND, OR, NOT)"
    )


class OutlineRequest(BaseModel):
    """Request to generate semantic outline."""

    content: str = Field(..., description="PSDL scenario content (YAML)")


class OutlineResponse(BaseModel):
    """Semantic outline of a PSDL scenario."""

    scenario: str = Field(..., description="Scenario name/identifier")
    version: Optional[str] = None
    description: Optional[str] = None
    signals: List[SignalOutline] = Field(default_factory=list)
    trends: List[TrendOutline] = Field(default_factory=list)
    logic: List[LogicOutline] = Field(default_factory=list)


# --- Export Models ---


class AuditInfo(BaseModel):
    """Audit block information extracted from scenario."""

    intent: Optional[str] = Field(None, description="What the scenario aims to detect")
    rationale: Optional[str] = Field(None, description="Clinical/scientific justification")
    provenance: Optional[str] = Field(None, description="Source reference (DOI, guideline)")


class ValidationResult(BaseModel):
    """Validation result included in certified bundle."""

    psdl_lang_version: str = Field(..., description="psdl-lang version used for validation")
    inspector_version: str = Field(..., description="Inspector version")
    valid: bool = Field(..., description="Whether scenario passed validation")
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationError] = Field(default_factory=list)


class ScenarioContent(BaseModel):
    """Scenario content in the bundle."""

    name: str = Field(..., description="Scenario identifier")
    version: Optional[str] = Field(None, description="Scenario version")
    raw_yaml: str = Field(..., description="Original YAML content")
    parsed: Dict[str, Any] = Field(..., description="Parsed IR from psdl-lang")


class ExportRequest(BaseModel):
    """Request to export audit bundle."""

    content: str = Field(..., description="PSDL scenario content (YAML)")
    format: str = Field("json", description="Export format: json or markdown")
    # Optional audit info provided by user
    intent: Optional[str] = Field(None, description="Scenario intent for audit")
    rationale: Optional[str] = Field(None, description="Clinical rationale")
    provenance: Optional[str] = Field(None, description="Source/reference")


class CertifiedBundle(BaseModel):
    """Certified Audit Bundle - the contract between Inspector and execution platforms."""

    bundle_version: str = Field("1.0", description="Bundle schema version")
    certified_at: str = Field(..., description="ISO 8601 timestamp")
    checksum: str = Field(..., description="SHA-256 checksum of scenario content")

    scenario: ScenarioContent = Field(..., description="Scenario content and parsed IR")
    validation: ValidationResult = Field(..., description="Validation results")
    audit: AuditInfo = Field(..., description="Audit trail information")
    summary: str = Field(..., description="Human-readable summary for IRB")


# Keep old name as alias for backward compatibility
ExportResponse = CertifiedBundle


# --- IRB Export Models ---


class GovernanceData(BaseModel):
    """User-provided governance narrative for IRB preparation."""

    clinical_summary: Optional[str] = Field(None, description="What the algorithm detects and why it matters clinically")
    justification: Optional[str] = Field(None, description="Why this algorithm is needed")
    risk_assessment: Optional[str] = Field(None, description="Consequences of false positives/negatives")


class IRBExportRequest(BaseModel):
    """Request to export Word document for IRB preparation."""

    content: str = Field(..., description="PSDL scenario content (YAML)")
    governance: GovernanceData = Field(default_factory=GovernanceData)
