"""Reranker implementations for vocabulary search.

Available rerankers:
- RuleBasedReranker: Domain-specific rules for OMOP concepts
- StringSimilarityReranker: Combines with Jaccard/Levenshtein
- HybridReranker: Combines multiple reranking strategies
- NoOpReranker: Pass-through (no reranking)

To add a new reranker:
1. Subclass BaseReranker
2. Implement rerank()
3. Register in factory.py
"""

from __future__ import annotations

from typing import List, Dict, Any
import re

from app.services.vocabulary_search.base import BaseReranker, VocabularySearchResult


class NoOpReranker(BaseReranker):
    """Pass-through reranker that doesn't modify scores."""

    def rerank(
        self,
        query: str,
        candidates: List[VocabularySearchResult],
        concepts_data: Dict[int, Dict[str, Any]],
    ) -> List[VocabularySearchResult]:
        for c in candidates:
            c.final_score = c.raw_score
        return sorted(candidates, key=lambda x: x.final_score, reverse=True)


class RuleBasedReranker(BaseReranker):
    """Reranker using domain-specific rules for OMOP/LOINC concepts.

    Rules are designed to prefer:
    - Base concepts over variants (e.g., "Creatinine" over "Creatinine reduction ratio")
    - Quantitative over qualitative tests
    - Standard specimens (Serum/Plasma) over unusual ones
    - Shorter, simpler names
    """

    # Patterns that indicate temporal/situational variants
    TEMPORAL_PATTERNS = [
        "--", " post ", " pre ", " days ", " hours ", " minutes ",
        " 1 hour", " 2 hour", " 4 hour", " 8 hour", " 12 hour", " 24 hour",
        "post dose", "post dialysis", "post challenge",
        " 10 ", " 15 ", " 30 ", " 60 ", " 90 ",
        "at first", "encounter", "baseline"
    ]

    SITUATIONAL_PATTERNS = [
        "sitting", "standing", "supine", "prone", "recumbent",
        "challenge", "stress", "exercise", "fasting",
        "minimum", "maximum", "mean", "average"
    ]

    NON_STANDARD_SPECIMENS = [
        "body fluid", "synovial", "peritoneal", "pleural",
        "cerebrospinal", "csf", "urine", "dialysis"
    ]

    # Common lab tests that should prefer Serum/Plasma
    SERUM_PLASMA_TESTS = ["creatinine", "glucose", "sodium", "potassium", "hemoglobin"]

    # Blood-test queries that are generic enough to prefer the unspecified-blood concept
    # over specimen-subtype variants (venous, arterial, capillary, cord, mixed venous).
    GENERIC_BLOOD_TESTS = ["hemoglobin", "hematocrit", "wbc", "platelet", "platelets"]

    BLOOD_SUBSPECIMENS = [
        "venous blood", "arterial blood", "capillary blood",
        "cord blood", "mixed venous", "peripheral blood",
    ]

    # Method/device qualifiers that surface for vitals when the query is generic.
    # E.g. "heart rate" should rank simple HR above "Heart rate Intra arterial line by Invasive".
    METHOD_DEVICE_PATTERNS = [
        "invasive", "non-invasive", "noninvasive",
        "intra arterial", "intra-arterial", "intraarterial",
        "arterial line", "central line",
        "doppler", "auscultation", "palpation", "oscillometric",
    ]

    # Generic vital-sign queries that should prefer a single measurement over panels.
    GENERIC_VITAL_QUERIES = [
        "heart rate", "blood pressure", "respiratory rate", "temperature",
        "pulse", "oxygen saturation", "spo2",
    ]

    PANEL_TOKENS = {"panel", "battery", "set"}

    def rerank(
        self,
        query: str,
        candidates: List[VocabularySearchResult],
        concepts_data: Dict[int, Dict[str, Any]],
    ) -> List[VocabularySearchResult]:
        query_lower = query.lower()

        for candidate in candidates:
            score = candidate.raw_score
            name_lower = candidate.concept_name.lower()
            concept_data = concepts_data.get(candidate.concept_id, {})

            # === BOOSTS ===

            # Exact name match
            if name_lower == query_lower:
                score += 0.5

            # Name starts with query
            elif name_lower.startswith(query_lower):
                score += 0.25

            # Core concept match (before brackets)
            core_name = name_lower.split("[")[0].strip()
            if core_name == query_lower:
                score += 0.3

            # Abbreviation match
            abbrevs = concept_data.get("abbreviations") or candidate.metadata.get("abbreviations") or []
            for abbrev in abbrevs:
                if abbrev and abbrev.lower() == query_lower:
                    score += 0.25
                    break

            # Search term match
            search_terms = concept_data.get("search_terms") or candidate.metadata.get("search_terms") or []
            for term in search_terms:
                if term and term.lower() == query_lower:
                    score += 0.2
                    break

            # Standard measurement in Serum/Plasma
            if "[mass/volume]" in name_lower and ("serum" in name_lower or "plasma" in name_lower):
                score += 0.15

            # Quantitative measurements preferred
            if "[mass/volume]" in name_lower:
                score += 0.1
            elif "[moles/volume]" in name_lower:
                score += 0.08

            # Plain "in Blood" for common tests
            if "in blood" in name_lower and "[mass/volume]" in name_lower:
                if not any(x in name_lower for x in ["arterial", "venous", "cord", "capillary", "mixed"]):
                    score += 0.1

            # === PENALTIES ===

            # Qualitative presence tests
            if "[presence]" in name_lower:
                score -= 0.2

            # Ratio concepts
            if "/" in name_lower and query_lower not in name_lower.split("/")[0]:
                score -= 0.2

            if "ratio" in name_lower:
                score -= 0.25

            # Timed variants
            if "--" in name_lower:
                score -= 0.25

            for pattern in self.TEMPORAL_PATTERNS:
                if pattern in name_lower:
                    score -= 0.15
                    break

            # Situational modifiers
            for pattern in self.SITUATIONAL_PATTERNS:
                if pattern in name_lower:
                    score -= 0.15
                    break

            # Non-standard specimens for common tests
            if query_lower in self.SERUM_PLASMA_TESTS:
                for specimen in self.NON_STANDARD_SPECIMENS:
                    if specimen in name_lower:
                        score -= 0.15
                        break

            # Specimen-subtype variants for generic blood-test queries
            # (hemoglobin -> prefer plain "in Blood" over "in Venous blood")
            if query_lower in self.GENERIC_BLOOD_TESTS:
                for variant in self.BLOOD_SUBSPECIMENS:
                    if variant in name_lower:
                        score -= 0.25
                        break

            # Method/device qualifiers for short generic vital-sign queries
            # (heart rate -> demote "Intra arterial line by Invasive")
            if len(query_lower.split()) <= 2:
                for pattern in self.METHOD_DEVICE_PATTERNS:
                    if pattern in name_lower:
                        score -= 0.3
                        break

            # Panel/battery composites for queries that mean a single measurement.
            # Penalty is sized to overcome the "name starts with query" boost (+0.25)
            # so a panel concept doesn't outrank an individual measurement.
            if query_lower in self.GENERIC_VITAL_QUERIES:
                name_tokens = re.findall(r"[a-z0-9]+", name_lower)
                if self.PANEL_TOKENS.intersection(name_tokens):
                    score -= 0.35

            # Method-specific variants
            if " by " in name_lower:
                score -= 0.1

            # Long names
            if len(name_lower) > 80:
                score -= 0.1
            elif len(name_lower) > 60:
                score -= 0.05

            # Short names bonus
            if len(name_lower) < 45:
                score += 0.05

            candidate.final_score = score

        return sorted(candidates, key=lambda x: x.final_score, reverse=True)


class StringSimilarityReranker(BaseReranker):
    """Reranker that combines embedding similarity with string similarity.

    Based on research showing hybrid approaches outperform pure embeddings.
    """

    def __init__(self, embedding_weight: float = 0.6, jaccard_weight: float = 0.2, edit_weight: float = 0.2):
        self.embedding_weight = embedding_weight
        self.jaccard_weight = jaccard_weight
        self.edit_weight = edit_weight

    def _jaccard_similarity(self, s1: str, s2: str) -> float:
        """Compute Jaccard similarity on word sets."""
        words1 = set(s1.lower().split())
        words2 = set(s2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

    def _normalized_edit_distance(self, s1: str, s2: str) -> float:
        """Compute normalized edit distance (1 = identical)."""
        s1, s2 = s1.lower(), s2.lower()
        if s1 == s2:
            return 1.0

        # Simple Levenshtein implementation
        m, n = len(s1), len(s2)
        if m == 0 or n == 0:
            return 0.0

        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if s1[i-1] == s2[j-1] else 1
                dp[i][j] = min(
                    dp[i-1][j] + 1,      # deletion
                    dp[i][j-1] + 1,      # insertion
                    dp[i-1][j-1] + cost  # substitution
                )

        edit_distance = dp[m][n]
        max_len = max(m, n)
        return 1.0 - (edit_distance / max_len)

    def rerank(
        self,
        query: str,
        candidates: List[VocabularySearchResult],
        concepts_data: Dict[int, Dict[str, Any]],
    ) -> List[VocabularySearchResult]:
        for candidate in candidates:
            # Get core name for comparison
            name = candidate.concept_name
            core_name = name.split("[")[0].strip()

            # Compute string similarities
            jaccard = self._jaccard_similarity(query, core_name)
            edit_sim = self._normalized_edit_distance(query, core_name)

            # Combine scores
            candidate.final_score = (
                self.embedding_weight * candidate.raw_score +
                self.jaccard_weight * jaccard +
                self.edit_weight * edit_sim
            )

        return sorted(candidates, key=lambda x: x.final_score, reverse=True)


class HybridReranker(BaseReranker):
    """Combines multiple rerankers in sequence."""

    def __init__(self, rerankers: List[BaseReranker]):
        self.rerankers = rerankers

    def rerank(
        self,
        query: str,
        candidates: List[VocabularySearchResult],
        concepts_data: Dict[int, Dict[str, Any]],
    ) -> List[VocabularySearchResult]:
        result = candidates
        for reranker in self.rerankers:
            # Each reranker uses the previous final_score as input
            for c in result:
                c.raw_score = c.final_score if c.final_score > 0 else c.raw_score
            result = reranker.rerank(query, result, concepts_data)
        return result


# Registry of available rerankers
RERANKER_REGISTRY = {
    "none": NoOpReranker,
    "rules": RuleBasedReranker,
    "string": StringSimilarityReranker,
    "hybrid": lambda: HybridReranker([StringSimilarityReranker(), RuleBasedReranker()]),
}


def get_reranker(name: str) -> BaseReranker:
    """Get reranker by name."""
    if name not in RERANKER_REGISTRY:
        raise ValueError(f"Unknown reranker: {name}. Available: {list(RERANKER_REGISTRY.keys())}")

    factory = RERANKER_REGISTRY[name]
    return factory() if callable(factory) else factory
