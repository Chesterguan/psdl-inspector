"""Terminology anchoring service for PSDL scenarios.

Extracts semantic references from scenarios and anchors them to OMOP
vocabulary concepts. This enables portable execution across different
sites that have their own datasetSpec.

Key insight: As more sites create datasetSpecs, the vocabulary mapping
problem solves itself - the community builds shared knowledge.

Search Strategy:
1. Primary: Semantic search using sentence embeddings (best accuracy)
2. Fallback: Keyword-based search if embeddings unavailable
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
import re

from psdl.core.ir import PSDLScenario

from app.models.schemas import TerminologyAnchor, TerminologyAnchors
from app.services.vocabulary import get_vocabulary_service

# Try to import modular search system (preferred)
_modular_search_available = False
try:
    from app.services.vocabulary_search import get_vocabulary_search_engine, SearchEngineConfig
    _modular_search_available = True
except ImportError:
    pass

# Fallback to legacy semantic search
_semantic_search_available = False
if not _modular_search_available:
    try:
        from app.services.vocabulary_semantic import get_semantic_vocabulary_search
        _semantic_search_available = True
    except ImportError:
        pass


class TerminologyAnchoringService:
    """Service to anchor semantic refs to OMOP vocabulary."""

    # Common signal reference aliases for search enhancement
    SIGNAL_ALIASES: Dict[str, List[str]] = {
        "creatinine": ["creatinine", "serum creatinine", "cr", "scr"],
        "bun": ["blood urea nitrogen", "bun", "urea nitrogen"],
        "heart_rate": ["heart rate", "pulse", "hr"],
        "body_temperature": ["body temperature", "temperature", "temp"],
        "systolic_bp": ["systolic blood pressure", "systolic bp", "sbp"],
        "diastolic_bp": ["diastolic blood pressure", "diastolic bp", "dbp"],
        "mean_arterial_pressure": ["mean arterial pressure", "map"],
        "oxygen_saturation": ["oxygen saturation", "spo2", "o2 sat"],
        "respiratory_rate": ["respiratory rate", "rr", "respiration"],
        "glucose": ["glucose", "blood glucose", "blood sugar"],
        "white_blood_cell_count": ["white blood cell", "wbc", "leukocyte"],
        "hemoglobin": ["hemoglobin", "hgb", "hb"],
        "platelet_count": ["platelet", "plt", "thrombocyte"],
        "sodium": ["sodium", "na"],
        "potassium": ["potassium", "k"],
        "lactate": ["lactate", "lactic acid"],
        "ph": ["ph", "blood ph", "arterial ph"],
        "pco2": ["pco2", "partial pressure co2", "carbon dioxide"],
        "po2": ["po2", "partial pressure o2", "oxygen"],
        "bicarbonate": ["bicarbonate", "hco3", "bicarb"],
        "troponin": ["troponin", "cardiac troponin", "trop"],
        "bnp": ["bnp", "brain natriuretic peptide", "b-type natriuretic"],
        "inr": ["inr", "international normalized ratio"],
        "ast": ["ast", "aspartate aminotransferase", "sgot"],
        "alt": ["alt", "alanine aminotransferase", "sgpt"],
        "bilirubin": ["bilirubin", "total bilirubin"],
        "albumin": ["albumin", "serum albumin"],
        "gfr": ["gfr", "glomerular filtration rate", "egfr"],
    }

    # Confidence thresholds
    HIGH_CONFIDENCE_SCORE = 100  # Exact match or known alias
    MEDIUM_CONFIDENCE_SCORE = 50  # Good fuzzy match
    LOW_CONFIDENCE_SCORE = 30  # Partial match

    def extract_refs_from_scenario(self, scenario: PSDLScenario) -> Set[str]:
        """Extract all semantic refs from a scenario.

        Collects refs from:
        - signals (ref field)
        - population criteria (future)
        - conditions (future)
        """
        refs = set()

        # Extract from signals
        if scenario.signals:
            for name, signal in scenario.signals.items():
                ref = signal.ref if signal.ref else name
                refs.add(ref)

        # Future: Extract from population.include/exclude criteria
        # Future: Extract from conditions, medications, etc.

        return refs

    def anchor_ref(self, ref: str) -> TerminologyAnchor:
        """Anchor a single semantic reference to OMOP vocabulary.

        Search strategy:
        1. Try semantic search first (embedding-based, most accurate)
        2. Fall back to keyword search if semantic not available

        Args:
            ref: The semantic reference (e.g., "creatinine", "heart_rate")

        Returns:
            TerminologyAnchor with match details and confidence level
        """
        # Normalize reference for search
        ref_lower = ref.lower().strip()
        ref_spaced = ref_lower.replace("_", " ").replace("-", " ")

        # Try modular search first (preferred, configurable)
        if _modular_search_available:
            try:
                return self._anchor_with_modular_search(ref_spaced, ref_lower)
            except Exception:
                pass

        # Try legacy semantic search
        if _semantic_search_available:
            try:
                return self._anchor_with_semantic_search(ref_spaced, ref_lower)
            except Exception:
                pass

        # Keyword-based search fallback
        return self._anchor_with_keyword_search(ref_spaced, ref_lower)

    def _anchor_with_modular_search(self, ref_spaced: str, ref_lower: str) -> TerminologyAnchor:
        """Anchor using modular search engine (configurable embedder/retriever/reranker)."""
        search_engine = get_vocabulary_search_engine()

        # Build search query
        search_query = ref_spaced

        # Expand with known medical context if available
        for alias_key, aliases in self.SIGNAL_ALIASES.items():
            if ref_lower == alias_key or ref_spaced in aliases:
                search_query = f"{ref_spaced} {' '.join(aliases[:2])}"
                break

        # Search
        results = search_engine.search(search_query, limit=5)

        if results:
            best = results[0]
            score = best.final_score

            # Determine confidence from score
            # Adjusted thresholds for combined scores (embedding + reranking)
            if score >= 1.0:
                confidence = "high"
            elif score >= 0.7:
                confidence = "medium"
            elif score >= 0.4:
                confidence = "low"
            else:
                confidence = "unanchored"

            # Get full concept data for unit extraction
            concept_data = search_engine.get_by_id(best.concept_id) or {}

            return TerminologyAnchor(
                concept_id=best.concept_id,
                concept_code=best.concept_code,
                vocabulary_id=best.vocabulary_id,
                concept_name=best.concept_name,
                domain_id=best.domain_id,
                standard_unit=self._extract_unit(concept_data),
                match_confidence=confidence,
            )

        return TerminologyAnchor(match_confidence="unanchored")

    def _anchor_with_semantic_search(self, ref_spaced: str, ref_lower: str) -> TerminologyAnchor:
        """Anchor using legacy semantic search (deprecated, use modular search)."""
        semantic_search = get_semantic_vocabulary_search()

        # Build search query - add context for better matching
        # "creatinine" -> "creatinine serum plasma measurement"
        search_query = ref_spaced

        # Expand with known medical context if available
        for alias_key, aliases in self.SIGNAL_ALIASES.items():
            if ref_lower == alias_key or ref_spaced in aliases:
                # Add aliases to query for better embedding
                search_query = f"{ref_spaced} {' '.join(aliases[:2])}"
                break

        # Search
        results = semantic_search.search(search_query, limit=5)

        if results:
            best = results[0]
            score = best.get("_semantic_score", 0)

            # Determine confidence from similarity score
            # Cosine similarity: 1.0 = identical, 0.0 = orthogonal
            if score >= 0.7:
                confidence = "high"
            elif score >= 0.5:
                confidence = "medium"
            elif score >= 0.3:
                confidence = "low"
            else:
                confidence = "unanchored"

            return TerminologyAnchor(
                concept_id=best.get("concept_id"),
                concept_code=best.get("concept_code"),
                vocabulary_id=best.get("vocabulary_id"),
                concept_name=best.get("concept_name"),
                domain_id=best.get("domain_id"),
                standard_unit=self._extract_unit(best),
                match_confidence=confidence,
            )

        return TerminologyAnchor(match_confidence="unanchored")

    def _anchor_with_keyword_search(self, ref_spaced: str, ref_lower: str) -> TerminologyAnchor:
        """Anchor using keyword-based search (fallback)."""
        vocab_service = get_vocabulary_service()

        # Build search queries from ref and known aliases
        search_queries = [ref_spaced]

        if ref_spaced != ref_lower:
            search_queries.append(ref_lower)

        # Expand with known aliases
        for alias_key, aliases in self.SIGNAL_ALIASES.items():
            if ref_lower == alias_key or ref_spaced in aliases or ref_lower.replace("_", "") == alias_key.replace("_", ""):
                search_queries.extend(aliases)
                break

        # Remove duplicates
        seen = set()
        unique_queries = []
        for q in search_queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)

        # Try each query
        best_match = None
        best_score = 0

        for query in unique_queries:
            results = vocab_service.search(query, limit=5)

            for result in results:
                score = result.get("_score", 0)

                # Boost abbreviation exact match
                if result.get("abbreviations"):
                    for abbrev in result["abbreviations"]:
                        if abbrev and abbrev.lower() == ref_lower:
                            score += 30

                if score > best_score:
                    best_score = score
                    best_match = result

        if best_match:
            if best_score >= self.HIGH_CONFIDENCE_SCORE:
                confidence = "high"
            elif best_score >= self.MEDIUM_CONFIDENCE_SCORE:
                confidence = "medium"
            else:
                confidence = "low"

            return TerminologyAnchor(
                concept_id=best_match.get("concept_id"),
                concept_code=best_match.get("concept_code"),
                vocabulary_id=best_match.get("vocabulary_id"),
                concept_name=best_match.get("concept_name"),
                domain_id=best_match.get("domain_id"),
                standard_unit=self._extract_unit(best_match),
                match_confidence=confidence,
            )

        return TerminologyAnchor(match_confidence="unanchored")

    def _extract_unit(self, concept: Dict[str, Any]) -> Optional[str]:
        """Extract standard unit from concept data."""
        # Check typical_units field
        if concept.get("typical_units"):
            units = concept["typical_units"]
            if isinstance(units, list) and units:
                first_unit = units[0]
                if isinstance(first_unit, dict):
                    return first_unit.get("code") or first_unit.get("name")
                return str(first_unit)

        # Check unit field directly
        return concept.get("unit")

    def anchor_scenario(self, scenario: PSDLScenario) -> TerminologyAnchors:
        """Anchor all semantic refs in a scenario to OMOP vocabulary.

        Args:
            scenario: Parsed PSDL scenario

        Returns:
            TerminologyAnchors with all anchors and statistics
        """
        refs = self.extract_refs_from_scenario(scenario)

        anchors: Dict[str, TerminologyAnchor] = {}
        unanchored_refs: List[str] = []

        for ref in refs:
            anchor = self.anchor_ref(ref)
            anchors[ref] = anchor

            if anchor.match_confidence == "unanchored":
                unanchored_refs.append(ref)

        anchored_count = len(refs) - len(unanchored_refs)

        return TerminologyAnchors(
            anchors=anchors,
            unanchored_refs=unanchored_refs,
            anchor_timestamp=datetime.now(timezone.utc).isoformat(),
            vocabulary_version=None,  # TODO: Get from vocabulary service
            total_refs=len(refs),
            anchored_count=anchored_count,
        )

    def anchor_from_parsed_dict(self, parsed: Dict[str, Any]) -> TerminologyAnchors:
        """Anchor refs from a parsed scenario dict (for raw YAML mode).

        Args:
            parsed: Parsed scenario dictionary

        Returns:
            TerminologyAnchors with all anchors
        """
        refs = set()

        # Extract from signals
        signals = parsed.get("signals", {})
        if isinstance(signals, dict):
            for name, signal_def in signals.items():
                if isinstance(signal_def, dict):
                    ref = signal_def.get("ref", name)
                else:
                    ref = name
                refs.add(ref)

        anchors: Dict[str, TerminologyAnchor] = {}
        unanchored_refs: List[str] = []

        for ref in refs:
            anchor = self.anchor_ref(ref)
            anchors[ref] = anchor

            if anchor.match_confidence == "unanchored":
                unanchored_refs.append(ref)

        anchored_count = len(refs) - len(unanchored_refs)

        return TerminologyAnchors(
            anchors=anchors,
            unanchored_refs=unanchored_refs,
            anchor_timestamp=datetime.now(timezone.utc).isoformat(),
            vocabulary_version=None,
            total_refs=len(refs),
            anchored_count=anchored_count,
        )


# Singleton instance
_terminology_anchoring_service: Optional[TerminologyAnchoringService] = None


def get_terminology_anchoring_service() -> TerminologyAnchoringService:
    """Get the terminology anchoring service singleton."""
    global _terminology_anchoring_service
    if _terminology_anchoring_service is None:
        _terminology_anchoring_service = TerminologyAnchoringService()
    return _terminology_anchoring_service
