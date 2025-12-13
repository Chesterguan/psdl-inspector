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
    """Audit block information."""

    intent: Optional[str] = None
    rationale: Optional[str] = None
    provenance: Optional[str] = None


class ExportRequest(BaseModel):
    """Request to export audit bundle."""

    content: str = Field(..., description="PSDL scenario content (YAML)")
    format: str = Field("json", description="Export format: json or markdown")


class ExportResponse(BaseModel):
    """Exported audit bundle."""

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Export metadata (timestamp, checksum)"
    )
    scenario: Dict[str, Any] = Field(..., description="Full parsed scenario")
    audit: AuditInfo = Field(..., description="Audit information")
    summary: str = Field(..., description="Human-readable summary")
