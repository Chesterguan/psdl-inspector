"""Semantic search for OMOP vocabulary using sentence embeddings.

Uses sentence-transformers for embedding and FAISS for fast similarity search.
Provides much better concept matching than keyword-based search.
"""

from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

# Lazy imports for optional dependencies
_sentence_transformer = None
_faiss = None


def _get_sentence_transformer():
    """Lazy load sentence-transformers."""
    global _sentence_transformer
    if _sentence_transformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_transformer = SentenceTransformer
        except ImportError:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
    return _sentence_transformer


def _get_faiss():
    """Lazy load faiss."""
    global _faiss
    if _faiss is None:
        try:
            import faiss
            _faiss = faiss
        except ImportError:
            raise ImportError("faiss not installed. Run: pip install faiss-cpu")
    return _faiss


# Paths
VOCAB_DIR = Path(__file__).parent.parent.parent / "data" / "vocabulary" / "enriched"
EMBEDDINGS_DIR = Path(__file__).parent.parent.parent / "data" / "vocabulary" / "embeddings"

# Model to use - MiniLM is fast and good for short text
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class SemanticVocabularySearch:
    """Semantic search for OMOP vocabulary concepts."""

    def __init__(self):
        self._model = None
        self._index = None
        self._concepts: List[Dict[str, Any]] = []
        self._loaded = False

    def _load_model(self):
        """Load the sentence transformer model."""
        if self._model is None:
            SentenceTransformer = _get_sentence_transformer()
            self._model = SentenceTransformer(EMBEDDING_MODEL)
        return self._model

    def _get_concept_text(self, concept: Dict[str, Any]) -> str:
        """Build searchable text from concept for embedding.

        Strategy: Keep it simple for better embedding quality.
        - Concept name (clean, without modifiers)
        - Abbreviations (important for matching)
        - Skip search terms (they can dilute the embedding)
        """
        name = concept["concept_name"]

        # Extract the core concept name without modifiers
        # E.g., "Creatinine [Mass/volume] in Serum or Plasma --7 days post XXX" -> "Creatinine"
        core_name = name.split("[")[0].strip()
        if " --" in name:
            # Has a modifier, extract just the base
            base_part = name.split(" --")[0]
        else:
            base_part = name

        parts = [core_name, base_part]

        # Add abbreviations (important for matching)
        if concept.get("abbreviations"):
            parts.extend(concept["abbreviations"][:3])  # Limit to first 3

        return " ".join(filter(None, set(parts)))

    def load(self) -> None:
        """Load vocabulary and embeddings."""
        if self._loaded:
            return

        faiss = _get_faiss()

        # Load vocabulary
        vocab_file = VOCAB_DIR / "vocabulary_final.json"
        if not vocab_file.exists():
            vocab_file = VOCAB_DIR / "vocabulary_partial.json"

        if not vocab_file.exists():
            raise FileNotFoundError(f"No vocabulary file found in {VOCAB_DIR}")

        with open(vocab_file) as f:
            self._concepts = json.load(f)

        # Try to load pre-computed embeddings
        embeddings_file = EMBEDDINGS_DIR / "concept_embeddings.pkl"
        index_file = EMBEDDINGS_DIR / "faiss_index.bin"

        if embeddings_file.exists() and index_file.exists():
            # Load pre-computed
            with open(embeddings_file, 'rb') as f:
                data = pickle.load(f)
                if data.get("model") == EMBEDDING_MODEL and len(data.get("concept_ids", [])) == len(self._concepts):
                    self._index = faiss.read_index(str(index_file))
                    self._loaded = True
                    return

        # Compute embeddings
        self._compute_embeddings()
        self._loaded = True

    def _compute_embeddings(self) -> None:
        """Compute and save embeddings for all concepts."""
        faiss = _get_faiss()
        model = self._load_model()

        print(f"Computing embeddings for {len(self._concepts)} concepts...")

        # Build text for each concept
        texts = [self._get_concept_text(c) for c in self._concepts]

        # Compute embeddings
        embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

        # Normalize for cosine similarity
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        # Build FAISS index
        dimension = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dimension)  # Inner product = cosine for normalized vectors
        self._index.add(embeddings.astype(np.float32))

        # Save for next time
        EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

        with open(EMBEDDINGS_DIR / "concept_embeddings.pkl", 'wb') as f:
            pickle.dump({
                "model": EMBEDDING_MODEL,
                "concept_ids": [c["concept_id"] for c in self._concepts],
            }, f)

        faiss.write_index(self._index, str(EMBEDDINGS_DIR / "faiss_index.bin"))
        print("Embeddings saved.")

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search concepts using semantic similarity with smart reranking.

        The search applies two stages:
        1. Semantic similarity using embeddings (recall)
        2. Reranking to prefer simpler, more canonical concepts (precision)

        Args:
            query: Search query (e.g., "creatinine", "serum creatinine level")
            limit: Maximum results to return

        Returns:
            List of concepts with similarity scores
        """
        self.load()
        model = self._load_model()

        # Embed query
        query_embedding = model.encode([query], convert_to_numpy=True)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)

        # Get more candidates for reranking
        num_candidates = min(limit * 20, 200)  # Get more candidates for better reranking
        scores, indices = self._index.search(query_embedding.astype(np.float32), num_candidates)

        query_lower = query.lower()

        candidates = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self._concepts):
                concept = self._concepts[idx].copy()
                semantic_score = float(score)

                # Apply reranking adjustments
                adjusted_score = semantic_score
                name_lower = concept["concept_name"].lower()

                # === STRONG BOOSTS for canonical/base concepts ===

                # BOOST: Exact name match
                if name_lower == query_lower:
                    adjusted_score += 0.5

                # BOOST: Name starts with query (e.g., "Creatinine [Mass/volume]...")
                elif name_lower.startswith(query_lower):
                    adjusted_score += 0.25

                # BOOST: Query is the core concept (before any brackets or modifiers)
                core_name = name_lower.split("[")[0].strip()
                if core_name == query_lower:
                    adjusted_score += 0.3

                # BOOST: Abbreviation exact match
                if concept.get("abbreviations"):
                    for abbrev in concept["abbreviations"]:
                        if abbrev and abbrev.lower() == query_lower:
                            adjusted_score += 0.25
                            break

                # BOOST: Search term exact match
                if concept.get("search_terms"):
                    for term in concept["search_terms"]:
                        if term and term.lower() == query_lower:
                            adjusted_score += 0.2
                            break

                # BOOST: Standard measurement pattern "[Mass/volume] in Serum or Plasma"
                # These are typically the canonical base concepts
                if "[mass/volume]" in name_lower and ("serum" in name_lower or "plasma" in name_lower):
                    adjusted_score += 0.15

                # BOOST: Quantitative measurements are usually preferred over qualitative
                if "[mass/volume]" in name_lower:
                    adjusted_score += 0.1
                elif "[moles/volume]" in name_lower:
                    adjusted_score += 0.08

                # PENALTY: Qualitative presence tests (usually not the primary measurement)
                if "[presence]" in name_lower:
                    adjusted_score -= 0.2

                # BOOST: Blood measurements for common tests (hemoglobin, glucose, etc.)
                if "in blood" in name_lower and "[mass/volume]" in name_lower:
                    if not any(x in name_lower for x in ["arterial", "venous", "cord", "capillary", "mixed"]):
                        adjusted_score += 0.1  # Plain "in Blood" is more general/base

                # BOOST: Standard vital sign without qualifiers
                if query_lower in ["heart rate", "respiratory rate", "body temperature"]:
                    if name_lower == query_lower or name_lower.startswith(query_lower + " ["):
                        adjusted_score += 0.2

                # === STRONG PENALTIES for derived/variant concepts ===

                # PENALTY: Ratio concepts (X/Y pattern) - these are derived
                if "/" in name_lower and query_lower not in name_lower.split("/")[0]:
                    adjusted_score -= 0.2

                # PENALTY: "ratio" in name (reduction ratio, clearance ratio, etc.)
                if "ratio" in name_lower:
                    adjusted_score -= 0.25

                # PENALTY: Temporal modifiers indicating timed measurements
                # "--" is a strong indicator of timed/situational variant (high penalty)
                if "--" in name_lower:
                    adjusted_score -= 0.25

                temporal_patterns = [
                    " post ", " pre ", " days ", " hours ", " minutes ",
                    " 1 hour", " 2 hour", " 4 hour", " 8 hour", " 12 hour", " 24 hour",
                    "post dose", "post dialysis", "post challenge",
                    " 10 ", " 15 ", " 30 ", " 60 ", " 90 ",
                    "at first", "encounter", "baseline"
                ]
                for pattern in temporal_patterns:
                    if pattern in name_lower:
                        adjusted_score -= 0.15
                        break

                # PENALTY: Positional/situational modifiers
                situational_patterns = [
                    "sitting", "standing", "supine", "prone", "recumbent",
                    "challenge", "stress", "exercise", "fasting",
                    "minimum", "maximum", "mean", "average"
                ]
                for pattern in situational_patterns:
                    if pattern in name_lower:
                        adjusted_score -= 0.15
                        break

                # PENALTY: Measurement in non-standard specimens for common labs
                if query_lower in ["creatinine", "glucose", "sodium", "potassium"]:
                    non_standard_specimens = [
                        "body fluid", "synovial", "peritoneal", "pleural",
                        "cerebrospinal", "csf", "urine", "dialysis"
                    ]
                    for specimen in non_standard_specimens:
                        if specimen in name_lower:
                            adjusted_score -= 0.15
                            break

                # PENALTY: Method-specific variants (e.g., "by Transthoracic impedance")
                if " by " in name_lower:
                    adjusted_score -= 0.1

                # PENALTY: Very long names (usually composite/derived)
                if len(name_lower) > 80:
                    adjusted_score -= 0.1
                elif len(name_lower) > 60:
                    adjusted_score -= 0.05

                # BOOST: Shorter, simpler names (more likely to be base concepts)
                if len(name_lower) < 45:
                    adjusted_score += 0.05

                concept["_semantic_score"] = adjusted_score
                concept["_raw_semantic_score"] = semantic_score
                candidates.append(concept)

        # Sort by adjusted score
        candidates.sort(key=lambda x: x["_semantic_score"], reverse=True)

        return candidates[:limit]

    def get_by_id(self, concept_id: int) -> Optional[Dict[str, Any]]:
        """Get concept by ID."""
        self.load()
        for concept in self._concepts:
            if concept["concept_id"] == concept_id:
                return concept
        return None


# Singleton
_semantic_search: Optional[SemanticVocabularySearch] = None


def get_semantic_vocabulary_search() -> SemanticVocabularySearch:
    """Get semantic vocabulary search singleton."""
    global _semantic_search
    if _semantic_search is None:
        _semantic_search = SemanticVocabularySearch()
    return _semantic_search
