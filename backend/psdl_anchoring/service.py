"""Terminology anchoring service for PSDL scenarios.

Canonical version: Workbench's domain-threaded anchor_ref(ref, psdl_domain, unit).
Domain filtering resolves lab/drug name collisions — e.g. 'creatinine' anchors
to a LOINC Measurement, not an RxNorm Drug, when psdl_domain='measurement'.

Search Strategy:
1. Primary: Semantic search using sentence embeddings (best accuracy)
2. Fallback: Keyword-based search if embeddings unavailable

Last updated: 2026-05-22
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set

from psdl.core.ir import PSDLScenario

from psdl_anchoring.models import TerminologyAnchor, TerminologyAnchors
from psdl_vocab import get_vocabulary_service

# Try to import modular search system (preferred)
_modular_search_available = False
try:
    from psdl_vocab_search import (
        get_vocabulary_search_engine,
        get_biolord_v2_engine,
        SearchEngineConfig,
    )
    _modular_search_available = True
except ImportError:
    pass


def _get_anchoring_engine():
    """Select the vocabulary search engine used by the modular anchoring path.

    Env-gated experiment toggle (default unchanged):
      ANCHORING_ENGINE=biolord_v2  -> the BioLORD v2 preset (get_biolord_v2_engine)
      anything else / unset        -> the default engine (get_vocabulary_search_engine)

    Lets the eval-report A/B the embedder while keeping production behavior the
    same until BioLORD is proven better; reversible by unsetting the env var.
    """
    if os.environ.get("ANCHORING_ENGINE") == "biolord_v2":
        return get_biolord_v2_engine()
    return get_vocabulary_search_engine()


class TerminologyAnchoringService:
    """Service to anchor semantic refs to OMOP vocabulary."""

    # PSDL signal domain → OMOP domain_id.
    # When a PSDL signal declares its domain, we filter the vocabulary search
    # to that OMOP domain to avoid lab/drug name collisions
    # (e.g. "creatinine" matches both LOINC Measurement and RxNorm Drug).
    PSDL_TO_OMOP_DOMAIN: Dict[str, str] = {
        "measurement": "Measurement",
        "laboratory": "Measurement",
        "lab": "Measurement",
        "vital": "Measurement",
        "vital_sign": "Measurement",
        "observation": "Observation",
        "condition": "Condition",
        "diagnosis": "Condition",
        "drug": "Drug",
        "medication": "Drug",
        "procedure": "Procedure",
    }

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
        # Condition / diagnosis aliases (used when anchoring condition-domain
        # signals; keeps `diabetes_diagnosis` from matching random concepts
        # that contain the token "diabetes").
        "diabetes": ["type 2 diabetes mellitus", "diabetes mellitus", "diabetes", "t2dm", "t2d"],
        "t2d": ["type 2 diabetes mellitus", "t2d", "t2dm"],
        "diabetes_diagnosis": ["type 2 diabetes mellitus", "diabetes mellitus"],
        "hypertension": ["essential hypertension", "hypertension", "htn"],
        "htn": ["essential hypertension", "hypertension", "htn"],
        "sepsis": ["sepsis", "septicemia"],
        "mi": ["myocardial infarction", "heart attack", "mi"],
        "afib": ["atrial fibrillation", "afib", "a fib"],
    }

    # Confidence thresholds
    HIGH_CONFIDENCE_SCORE = 100  # Exact match or known alias
    MEDIUM_CONFIDENCE_SCORE = 50  # Good fuzzy match
    LOW_CONFIDENCE_SCORE = 30  # Partial match

    def extract_refs_from_scenario(self, scenario: PSDLScenario) -> Set[str]:
        """Extract all semantic refs from a scenario (string-only view).

        For domain-aware anchoring, use `extract_signals_from_scenario` which
        returns (ref, domain, unit) tuples. This method is kept for backward
        compat with any caller that only needs the set of ref strings.
        """
        return {ref for ref, _, _ in self.extract_signals_from_scenario(scenario)}

    def extract_signals_from_scenario(
        self, scenario: PSDLScenario
    ) -> List[tuple]:
        """Extract (ref, psdl_domain, unit) for every signal in a scenario.

        Returns a list (not a set) because two signals may share the same ref
        but differ in domain/unit (e.g. two separate creatinine signals under
        different aliases).
        """
        out: List[tuple] = []
        if scenario.signals:
            for name, signal in scenario.signals.items():
                ref = signal.ref if signal.ref else name
                domain = getattr(signal, "domain", None)
                unit = getattr(signal, "unit", None)
                out.append((ref, domain, unit))
        return out

    def anchor_ref(
        self,
        ref: str,
        psdl_domain: Optional[str] = None,
        unit: Optional[str] = None,
    ) -> TerminologyAnchor:
        """Anchor a single semantic reference to OMOP vocabulary.

        Search strategy:
        1. Try semantic search first (embedding-based, most accurate)
        2. Fall back to keyword search if semantic not available

        Args:
            ref: The semantic reference (e.g., "creatinine", "heart_rate")
            psdl_domain: The PSDL signal domain (e.g., "measurement", "drug",
                "condition"). When provided, the vocabulary search is filtered
                to the matching OMOP domain — this resolves lab/drug name
                collisions like "creatinine" (LOINC lab vs RxNorm ingredient).
            unit: The signal unit (e.g., "mg/dL"). Reserved for future
                unit-aware disambiguation; currently unused.

        Returns:
            TerminologyAnchor with match details and confidence level
        """
        # Normalize reference for search
        ref_lower = ref.lower().strip()
        ref_spaced = ref_lower.replace("_", " ").replace("-", " ")
        # psdl-lang returns `domain` as a Domain enum; use its string value
        # (plain strings pass through unchanged). Without this the .strip()
        # calls below raise and anchoring is silently skipped.
        # ponytail: coerce here, don't re-type the whole chain.
        psdl_domain = getattr(psdl_domain, "value", psdl_domain)
        omop_domain = self._psdl_domain_to_omop(psdl_domain)

        # Demographic signals (age, sex, race, ...) are computed from
        # PATIENT-table columns, not looked up in a vocabulary. Return an
        # intentional "unanchored" result so the UI treats them as derived.
        if psdl_domain and psdl_domain.strip().lower() == "demographic":
            return TerminologyAnchor(match_confidence="unanchored")

        # Try modular search first (preferred, configurable)
        if _modular_search_available:
            try:
                return self._anchor_with_modular_search(ref_spaced, ref_lower, omop_domain)
            except Exception:
                pass

        # Keyword-based search fallback
        return self._anchor_with_keyword_search(ref_spaced, ref_lower, omop_domain)

    def _psdl_domain_to_omop(self, psdl_domain: Optional[str]) -> Optional[str]:
        """Translate a PSDL signal domain to the OMOP CDM domain_id.

        Returns None when the domain is unknown, missing, or is a non-OMOP
        category (e.g., `demographic` — age lives on PATIENT directly, not
        in the vocabulary).
        """
        if not psdl_domain:
            return None
        return self.PSDL_TO_OMOP_DOMAIN.get(psdl_domain.strip().lower())

    def _anchor_with_modular_search(
        self,
        ref_spaced: str,
        ref_lower: str,
        omop_domain: Optional[str] = None,
    ) -> TerminologyAnchor:
        """Anchor using modular search engine (configurable embedder/retriever/reranker)."""
        search_engine = _get_anchoring_engine()

        # Build search query
        search_query = ref_spaced

        # Expand with known medical context if available
        for alias_key, aliases in self.SIGNAL_ALIASES.items():
            if ref_lower == alias_key or ref_spaced in aliases:
                search_query = f"{ref_spaced} {' '.join(aliases[:2])}"
                break

        # Search. The modular engine may not expose a domain filter — if it
        # doesn't, we post-filter the results by domain below.
        try:
            results = search_engine.search(search_query, limit=5, domain=omop_domain)
        except TypeError:
            # Older search engine without domain kwarg — fetch more, filter after.
            results = search_engine.search(search_query, limit=20)
            if omop_domain:
                results = [r for r in results if r.domain_id == omop_domain][:5]

        # If the domain filter eliminated every match, fall through with the
        # keyword engine (which always supports domain filtering).
        if not results and omop_domain:
            return self._anchor_with_keyword_search(ref_spaced, ref_lower, omop_domain)

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

    def _anchor_with_keyword_search(
        self,
        ref_spaced: str,
        ref_lower: str,
        omop_domain: Optional[str] = None,
    ) -> TerminologyAnchor:
        """Anchor using keyword-based search (fallback)."""
        vocab_service = get_vocabulary_service()

        # Build search queries from ref and known aliases.
        # If the ref already has multiple tokens (e.g. "serum creatinine"),
        # don't expand to the generic alias set — that broadens the query
        # and lets short, unqualified matches outrank the specific one.
        # Alias expansion only kicks in for single-token refs.
        search_queries = [ref_spaced]

        if ref_spaced != ref_lower:
            search_queries.append(ref_lower)

        tokens = ref_spaced.split()
        is_single_token = len(tokens) == 1
        if is_single_token:
            for alias_key, aliases in self.SIGNAL_ALIASES.items():
                if (
                    ref_lower == alias_key
                    or ref_spaced in aliases
                    or ref_lower.replace("_", "") == alias_key.replace("_", "")
                ):
                    search_queries.extend(aliases)
                    break
        else:
            # Multi-token ref — keep the full ref as primary, but if any
            # token matches an alias key, add that alias's canonical form as
            # a fallback. E.g. "baseline_creatinine" falls back to
            # "creatinine", "diabetes_diagnosis" falls back to "type 2
            # diabetes mellitus". Fallback queries are only used when the
            # primary query returned no match (see break-on-first-hit below).
            for tok in tokens:
                if tok in self.SIGNAL_ALIASES:
                    aliases = self.SIGNAL_ALIASES[tok]
                    # Keep the first (canonical) alias only — minimise drift.
                    if aliases and aliases[0] not in search_queries:
                        search_queries.append(aliases[0])

        # Remove duplicates
        seen = set()
        unique_queries = []
        for q in search_queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)

        # Try each query — with domain filter when the PSDL signal declared one.
        # Scores from different queries are NOT comparable (a broad query like
        # "creatinine" produces higher raw scores than a narrow one like
        # "serum creatinine"), so we prefer the first query's top hit and only
        # fall back to later queries when earlier ones returned nothing.
        best_match = None
        best_score = 0

        for query in unique_queries:
            results = vocab_service.search(query, limit=5, domain=omop_domain)

            # Fallback: if a domain filter returned nothing (the demo vocab
            # doesn't have a matching domain concept), retry without the
            # filter so the caller at least sees a "low confidence" anchor
            # instead of silently getting unanchored.
            if not results and omop_domain:
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

            # Once we've locked onto a reasonably-confident match from an
            # earlier, more specific query, don't let broader alias queries
            # overwrite it. But if the primary query only produced a low-
            # confidence hit, keep trying fallbacks — compound refs like
            # `baseline_creatinine` or `diabetes_diagnosis` often need the
            # single-token fallback to find the canonical concept.
            if best_score >= self.MEDIUM_CONFIDENCE_SCORE:
                break

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

        Uses each signal's PSDL `domain` to filter the vocabulary search, so
        measurement signals can't accidentally resolve to a drug concept with
        the same name (and vice versa).

        Args:
            scenario: Parsed PSDL scenario

        Returns:
            TerminologyAnchors with all anchors and statistics
        """
        signals = self.extract_signals_from_scenario(scenario)
        return self._anchor_signals(signals)

    def anchor_from_parsed_dict(self, parsed: Dict[str, Any]) -> TerminologyAnchors:
        """Anchor refs from a parsed scenario dict (for raw YAML mode).

        Args:
            parsed: Parsed scenario dictionary

        Returns:
            TerminologyAnchors with all anchors
        """
        signals: List[tuple] = []

        raw_signals = parsed.get("signals", {})
        if isinstance(raw_signals, dict):
            for name, signal_def in raw_signals.items():
                if isinstance(signal_def, dict):
                    ref = signal_def.get("ref", name)
                    domain = signal_def.get("domain")
                    unit = signal_def.get("unit")
                else:
                    ref, domain, unit = name, None, None
                signals.append((ref, domain, unit))

        return self._anchor_signals(signals)

    def _anchor_signals(self, signals: List[tuple]) -> TerminologyAnchors:
        """Run anchor_ref for a list of (ref, domain, unit) tuples.

        Deduplicates on (ref, domain) — two signals with the same ref but
        different domains must be anchored independently because they resolve
        to different vocabulary concepts.
        """
        anchors: Dict[str, TerminologyAnchor] = {}
        unanchored_refs: List[str] = []
        seen: Set[tuple] = set()

        for ref, domain, unit in signals:
            key = (ref, domain)
            if key in seen:
                continue
            seen.add(key)

            anchor = self.anchor_ref(ref, psdl_domain=domain, unit=unit)
            anchors[ref] = anchor
            if anchor.match_confidence == "unanchored":
                unanchored_refs.append(ref)

        total = len(seen)
        anchored_count = total - len(unanchored_refs)

        return TerminologyAnchors(
            anchors=anchors,
            unanchored_refs=unanchored_refs,
            anchor_timestamp=datetime.now(timezone.utc).isoformat(),
            vocabulary_version=None,
            total_refs=total,
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
