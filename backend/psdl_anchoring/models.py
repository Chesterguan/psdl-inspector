"""Terminology anchor data models — OMOP vocabulary bindings for PSDL semantic refs."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


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
