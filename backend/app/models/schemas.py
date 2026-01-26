"""Pydantic models for API schemas."""

from __future__ import annotations
from typing import Any, Optional, List, Dict, Literal
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


# --- Terminology Anchors Models ---


class TerminologyAnchor(BaseModel):
    """Single terminology anchor for a semantic reference."""

    concept_id: Optional[int] = Field(None, description="OMOP concept ID")
    concept_code: Optional[str] = Field(None, description="Vocabulary-specific code (e.g., LOINC code)")
    vocabulary_id: Optional[str] = Field(None, description="Source vocabulary (e.g., LOINC, SNOMED)")
    concept_name: Optional[str] = Field(None, description="Standard concept name")
    domain_id: Optional[str] = Field(None, description="OMOP domain (Measurement, Condition, Drug, etc.)")
    standard_unit: Optional[str] = Field(None, description="Standard unit for measurements")
    match_confidence: Literal["high", "medium", "low", "unanchored"] = Field(
        "unanchored", description="Confidence level of the vocabulary match"
    )


class TerminologyAnchors(BaseModel):
    """All terminology anchors for a scenario - OMOP vocabulary binding."""

    anchors: Dict[str, TerminologyAnchor] = Field(
        default_factory=dict, description="Map of semantic refs to their OMOP anchors"
    )
    unanchored_refs: List[str] = Field(
        default_factory=list, description="Refs that couldn't be matched to vocabulary"
    )
    anchor_timestamp: str = Field(..., description="When anchoring was performed (ISO 8601)")
    vocabulary_version: Optional[str] = Field(None, description="OMOP vocabulary version used")
    total_refs: int = Field(0, description="Total number of refs processed")
    anchored_count: int = Field(0, description="Number of successfully anchored refs")


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

    bundle_version: str = Field("1.1", description="Bundle schema version")
    certified_at: str = Field(..., description="ISO 8601 timestamp")
    checksum: str = Field(..., description="SHA-256 checksum of scenario content")

    scenario: ScenarioContent = Field(..., description="Scenario content and parsed IR")
    terminology_anchors: Optional[TerminologyAnchors] = Field(
        None, description="OMOP vocabulary binding for semantic refs"
    )
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


# --- Generation Models ---


class GenerateRequest(BaseModel):
    """Request to generate PSDL scenario from natural language."""

    prompt: str = Field(..., description="Natural language description of the clinical scenario")
    provider: str = Field("openai", description="LLM provider: 'openai' or 'ollama'")
    model: Optional[str] = Field(None, description="Optional model override (e.g., 'gpt-4o-mini', 'mistral-small')")
    max_retries: int = Field(3, ge=0, le=5, description="Max correction attempts if validation fails (0-5)")
    clinical_context: Optional[str] = Field(None, description="Optional clinical guidelines or reference text to include")


class EnrichmentDetail(BaseModel):
    """Details about a single signal enrichment."""

    signal: str = Field(..., description="Signal name in the YAML")
    ref: str = Field(..., description="Signal reference used for lookup")
    matched_concept: Optional[str] = Field(None, description="Matched OMOP concept name")
    concept_id: Optional[int] = Field(None, description="OMOP concept ID")
    concept_code: Optional[str] = Field(None, description="Concept code (e.g., LOINC code)")
    vocabulary_id: Optional[str] = Field(None, description="Source vocabulary (e.g., LOINC)")
    unit: Optional[str] = Field(None, description="Enriched unit")
    error: Optional[str] = Field(None, description="Error message if enrichment failed")


class EnrichmentSummary(BaseModel):
    """Summary of vocabulary enrichment results."""

    total_signals: int = Field(0, description="Total number of signals processed")
    matched: int = Field(0, description="Number of signals matched to vocabulary")
    unmatched: int = Field(0, description="Number of signals without matches")
    success_rate: float = Field(0.0, description="Percentage of signals matched")
    details: List[EnrichmentDetail] = Field(default_factory=list, description="Per-signal enrichment details")


class GenerateResponse(BaseModel):
    """Response from scenario generation."""

    yaml: str = Field(..., description="Generated PSDL YAML (enriched with vocabulary if available)")
    valid: bool = Field(..., description="Whether generated YAML is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    attempts: int = Field(1, description="Number of generation/correction attempts made")
    enrichment: Optional[EnrichmentSummary] = Field(None, description="Vocabulary enrichment results")
