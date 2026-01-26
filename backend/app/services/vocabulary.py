"""Vocabulary service for OMOP concept lookup and search.

Provides fast in-memory search across enriched clinical vocabulary
with support for concept names, abbreviations, and search terms.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from functools import lru_cache


# Path to enriched vocabulary (use partial until full is ready)
VOCAB_DIR = Path(__file__).parent.parent.parent / "data" / "vocabulary" / "enriched"


class VocabularyService:
    """Service for searching enriched OMOP vocabulary."""

    def __init__(self):
        self._concepts: List[Dict[str, Any]] = []
        self._by_id: Dict[int, Dict[str, Any]] = {}
        self._search_index: Dict[str, List[int]] = {}  # term -> concept_ids
        self._loaded = False

    def load(self) -> None:
        """Load vocabulary from JSON file."""
        if self._loaded:
            return

        # Try final file first, fall back to partial
        vocab_file = VOCAB_DIR / "vocabulary_final.json"
        if not vocab_file.exists():
            vocab_file = VOCAB_DIR / "vocabulary_partial.json"

        if not vocab_file.exists():
            raise FileNotFoundError(f"No vocabulary file found in {VOCAB_DIR}")

        with open(vocab_file) as f:
            self._concepts = json.load(f)

        # Build indexes
        self._build_indexes()
        self._loaded = True

    def _build_indexes(self) -> None:
        """Build search indexes for fast lookup."""
        for concept in self._concepts:
            concept_id = concept["concept_id"]
            self._by_id[concept_id] = concept

            # Index by concept name (tokenized)
            self._index_text(concept["concept_name"], concept_id)

            # Index by abbreviations
            if concept.get("abbreviations"):
                for abbrev in concept["abbreviations"]:
                    self._index_text(abbrev, concept_id, exact=True)

            # Index by search terms
            if concept.get("search_terms"):
                for term in concept["search_terms"]:
                    self._index_text(term, concept_id)

            # Index by concept code
            self._index_text(concept.get("concept_code", ""), concept_id, exact=True)

    def _index_text(self, text: str, concept_id: int, exact: bool = False) -> None:
        """Add text to search index."""
        if not text:
            return

        text_lower = text.lower().strip()

        if exact:
            # Index exact match only
            if text_lower not in self._search_index:
                self._search_index[text_lower] = []
            if concept_id not in self._search_index[text_lower]:
                self._search_index[text_lower].append(concept_id)
        else:
            # Index each token
            tokens = re.split(r'[\s\-_/\[\]()]+', text_lower)
            for token in tokens:
                if len(token) >= 2:  # Skip single chars
                    if token not in self._search_index:
                        self._search_index[token] = []
                    if concept_id not in self._search_index[token]:
                        self._search_index[token].append(concept_id)

    def get_by_id(self, concept_id: int) -> Optional[Dict[str, Any]]:
        """Get concept by ID."""
        self.load()
        return self._by_id.get(concept_id)

    def search(
        self,
        query: str,
        limit: int = 20,
        category: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search concepts by query string.

        Searches across concept names, abbreviations, and search terms.
        Returns results ranked by relevance.

        Ranking priorities:
        1. Exact name match or search term match (highest)
        2. Name starts with query (primary concept)
        3. Abbreviation exact match
        4. Search term contains query
        5. Token matches (with penalty for ratios/panels)
        """
        self.load()

        if not query or len(query) < 2:
            return []

        query_lower = query.lower().strip()
        tokens = re.split(r'[\s\-_/\[\]()]+', query_lower)
        tokens = [t for t in tokens if len(t) >= 2]

        if not tokens:
            return []

        # Score concepts by match quality
        scores: Dict[int, float] = {}

        # Exact match on full query in index (high score)
        if query_lower in self._search_index:
            for cid in self._search_index[query_lower]:
                scores[cid] = scores.get(cid, 0) + 50

        # Token matches (base score)
        for token in tokens:
            if token in self._search_index:
                for cid in self._search_index[token]:
                    scores[cid] = scores.get(cid, 0) + 10

            # Prefix match (for autocomplete) - lower score
            for indexed_term, cids in self._search_index.items():
                if indexed_term.startswith(token) and indexed_term != token:
                    for cid in cids:
                        scores[cid] = scores.get(cid, 0) + 3

        # Apply smart ranking adjustments
        for cid in list(scores.keys()):
            concept = self._by_id[cid]
            name_lower = concept["concept_name"].lower()

            # BOOST: Exact name match
            if name_lower == query_lower:
                scores[cid] += 200

            # BOOST: Name starts with query (primary concept, not ratio)
            if name_lower.startswith(query_lower):
                scores[cid] += 100

            # BOOST: Abbreviation exact match
            if concept.get("abbreviations"):
                for abbrev in concept["abbreviations"]:
                    if abbrev and abbrev.lower() == query_lower:
                        scores[cid] += 150
                    elif abbrev and abbrev.lower() in tokens:
                        scores[cid] += 50

            # BOOST: Search term exact match
            if concept.get("search_terms"):
                for term in concept["search_terms"]:
                    if term:
                        term_lower = term.lower()
                        if term_lower == query_lower:
                            scores[cid] += 150
                        elif query_lower in term_lower:
                            scores[cid] += 30

            # PENALTY: Ratio concepts (X/Y pattern) - query is secondary
            if "/" in name_lower:
                # Check if query appears after the /
                parts = name_lower.split("/")
                if len(parts) >= 2:
                    before_slash = parts[0]
                    # If query is NOT in the part before slash, it's secondary
                    if query_lower not in before_slash:
                        scores[cid] -= 40

            # PENALTY: Panel concepts (contains "panel" or "and")
            if " panel" in name_lower or " and " in name_lower:
                scores[cid] -= 30

            # PENALTY: Very long names (usually composite/complex)
            if len(name_lower) > 80:
                scores[cid] -= 20

            # BOOST: Shorter, more specific names
            if len(name_lower) < 50:
                scores[cid] += 15

        # Filter by category/domain if specified
        if category or domain:
            filtered_scores = {}
            for cid, score in scores.items():
                concept = self._by_id[cid]
                if category and concept.get("category") != category:
                    continue
                if domain and concept.get("domain_id") != domain:
                    continue
                filtered_scores[cid] = score
            scores = filtered_scores

        # Sort by score and return top results
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        results = []
        for cid in sorted_ids[:limit]:
            concept = self._by_id[cid].copy()
            concept["_score"] = scores[cid]
            results.append(concept)

        # If no results, try fuzzy matching
        if not results and len(query_lower) >= 3:
            results = self._fuzzy_search(query_lower, limit)

        return results

    def _fuzzy_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fallback fuzzy search using simple substring matching."""
        results = []
        query_lower = query.lower()

        for concept in self._concepts:
            score = 0
            name_lower = concept["concept_name"].lower()

            # Check if query is substring of concept name
            if query_lower in name_lower:
                score = 30

            # Check abbreviations for partial match
            if concept.get("abbreviations"):
                for abbrev in concept["abbreviations"]:
                    if abbrev and query_lower in abbrev.lower():
                        score = max(score, 40)

            # Check search terms for partial match
            if concept.get("search_terms"):
                for term in concept["search_terms"]:
                    if term and query_lower in term.lower():
                        score = max(score, 35)

            if score > 0:
                result = concept.copy()
                result["_score"] = score
                result["_match_type"] = "fuzzy"
                results.append(result)

        # Sort by score and return top results
        results.sort(key=lambda x: x["_score"], reverse=True)
        return results[:limit]

    def autocomplete(
        self,
        prefix: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get autocomplete suggestions for a prefix.

        Returns lightweight results optimized for dropdown display.
        """
        self.load()

        if not prefix or len(prefix) < 2:
            return []

        prefix_lower = prefix.lower().strip()

        # Find matching concepts
        matching_ids = set()

        # Check exact prefix matches in index
        for term, cids in self._search_index.items():
            if term.startswith(prefix_lower):
                matching_ids.update(cids)

        # Score by relevance
        results = []
        for cid in matching_ids:
            concept = self._by_id[cid]

            # Calculate simple relevance score
            score = 0
            name_lower = concept["concept_name"].lower()

            if name_lower.startswith(prefix_lower):
                score += 100
            elif prefix_lower in name_lower:
                score += 50

            # Boost abbreviation matches
            if concept.get("abbreviations"):
                for abbrev in concept["abbreviations"]:
                    if abbrev and abbrev.lower().startswith(prefix_lower):
                        score += 80

            results.append({
                "concept_id": concept["concept_id"],
                "concept_name": concept["concept_name"],
                "concept_code": concept.get("concept_code"),
                "category": concept.get("category"),
                "abbreviations": concept.get("abbreviations"),
                "_score": score,
            })

        # Sort and limit
        results.sort(key=lambda x: x["_score"], reverse=True)
        return results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get vocabulary statistics."""
        self.load()

        categories = {}
        for concept in self._concepts:
            cat = concept.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_concepts": len(self._concepts),
            "indexed_terms": len(self._search_index),
            "categories": categories,
        }


# Singleton instance
_vocabulary_service: Optional[VocabularyService] = None


def get_vocabulary_service() -> VocabularyService:
    """Get the vocabulary service singleton."""
    global _vocabulary_service
    if _vocabulary_service is None:
        _vocabulary_service = VocabularyService()
    return _vocabulary_service
