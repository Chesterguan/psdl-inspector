"""SQLite-based vocabulary service with embedding support for semantic search.

Provides fast semantic search across enriched clinical vocabulary using
OpenAI text-embedding-3-small embeddings stored in SQLite databases.
"""

from __future__ import annotations

import sqlite3
import struct
import json
import ast
from pathlib import Path
from typing import List, Optional, Dict, Any
from functools import lru_cache
import os

import numpy as np


def safe_json_loads(value: str) -> Any:
    """Parse JSON string, falling back to ast.literal_eval for Python dict strings."""
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return None

# Paths to enriched vocabulary databases
VOCAB_DIR = Path(__file__).parent.parent.parent / "data" / "vocabulary"
LOINC_DB = VOCAB_DIR / "loinc_enriched.db"
POPULATION_DB = VOCAB_DIR / "population_enriched.db"

# Embedding dimension for text-embedding-3-small
EMBEDDING_DIM = 1536


def unpack_embedding(blob: bytes) -> np.ndarray:
    """Unpack embedding from SQLite BLOB to numpy array."""
    return np.array(struct.unpack(f'{EMBEDDING_DIM}f', blob), dtype=np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


class SemanticVocabularyService:
    """Service for semantic search across enriched OMOP vocabulary using embeddings."""

    def __init__(self):
        self._loinc_conn: Optional[sqlite3.Connection] = None
        self._population_conn: Optional[sqlite3.Connection] = None
        self._openai_client = None
        self._loinc_embeddings: Dict[int, np.ndarray] = {}
        self._population_embeddings: Dict[int, np.ndarray] = {}
        self._loinc_concepts: Dict[int, Dict[str, Any]] = {}
        self._population_concepts: Dict[int, Dict[str, Any]] = {}
        self._loaded_loinc = False
        self._loaded_population = False

    def _get_openai_client(self):
        """Get OpenAI client for generating query embeddings."""
        if self._openai_client is None:
            from openai import OpenAI
            self._openai_client = OpenAI()
        return self._openai_client

    def _load_loinc(self) -> None:
        """Load LOINC vocabulary from SQLite."""
        if self._loaded_loinc:
            return

        if not LOINC_DB.exists():
            raise FileNotFoundError(f"LOINC database not found: {LOINC_DB}")

        self._loinc_conn = sqlite3.connect(str(LOINC_DB))
        self._loinc_conn.row_factory = sqlite3.Row

        # Load all concepts with embeddings
        cursor = self._loinc_conn.execute("""
            SELECT concept_id, concept_code, concept_name, vocabulary_id, domain_id,
                   concept_class_id, abbreviations, search_terms, category, typical_units, embedding
            FROM concepts WHERE embedding IS NOT NULL
        """)

        for row in cursor:
            concept_id = row['concept_id']
            # Parse typical_units - may be a dict or list
            typical_units = safe_json_loads(row['typical_units']) if row['typical_units'] else []
            # Ensure it's a list
            if isinstance(typical_units, dict):
                typical_units = [typical_units]

            self._loinc_concepts[concept_id] = {
                'concept_id': concept_id,
                'concept_code': row['concept_code'],
                'concept_name': row['concept_name'],
                'vocabulary_id': row['vocabulary_id'],
                'domain_id': row['domain_id'],
                'concept_class_id': row['concept_class_id'],
                'abbreviations': safe_json_loads(row['abbreviations']) or [],
                'search_terms': safe_json_loads(row['search_terms']) or [],
                'category': row['category'],
                'typical_units': typical_units,
            }
            if row['embedding']:
                self._loinc_embeddings[concept_id] = unpack_embedding(row['embedding'])

        self._loaded_loinc = True

    def _load_population(self) -> None:
        """Load population vocabulary (SNOMED + RxNorm) from SQLite."""
        if self._loaded_population:
            return

        if not POPULATION_DB.exists():
            raise FileNotFoundError(f"Population database not found: {POPULATION_DB}")

        self._population_conn = sqlite3.connect(str(POPULATION_DB))
        self._population_conn.row_factory = sqlite3.Row

        # Load all concepts with embeddings
        cursor = self._population_conn.execute("""
            SELECT concept_id, concept_code, concept_name, vocabulary_id, domain_id,
                   concept_class_id, abbreviations, search_terms, category, embedding
            FROM concepts WHERE embedding IS NOT NULL
        """)

        for row in cursor:
            concept_id = row['concept_id']
            self._population_concepts[concept_id] = {
                'concept_id': concept_id,
                'concept_code': row['concept_code'],
                'concept_name': row['concept_name'],
                'vocabulary_id': row['vocabulary_id'],
                'domain_id': row['domain_id'],
                'concept_class_id': row['concept_class_id'],
                'abbreviations': safe_json_loads(row['abbreviations']) or [],
                'search_terms': safe_json_loads(row['search_terms']) or [],
                'category': row['category'],
            }
            if row['embedding']:
                self._population_embeddings[concept_id] = unpack_embedding(row['embedding'])

        self._loaded_population = True

    def _get_query_embedding(self, query: str) -> np.ndarray:
        """Generate embedding for a search query."""
        client = self._get_openai_client()
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        return np.array(response.data[0].embedding, dtype=np.float32)

    def search_loinc(
        self,
        query: str,
        limit: int = 20,
        category: Optional[str] = None,
        use_semantic: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search LOINC vocabulary using semantic similarity.

        Args:
            query: Search query string
            limit: Maximum number of results
            category: Filter by category (lab_chemistry, vital_sign, etc.)
            use_semantic: Whether to use semantic (embedding) search

        Returns:
            List of matching concepts with similarity scores
        """
        self._load_loinc()

        if not query or len(query) < 2:
            return []

        # Get query embedding
        if use_semantic and self._loinc_embeddings:
            try:
                query_embedding = self._get_query_embedding(query)
            except Exception:
                # Fallback to text search if embedding fails
                use_semantic = False

        results = []
        query_lower = query.lower()

        for concept_id, concept in self._loinc_concepts.items():
            # Apply category filter
            if category and concept.get('category') != category:
                continue

            score = 0.0

            if use_semantic and concept_id in self._loinc_embeddings:
                # Semantic similarity score (0-1)
                score = cosine_similarity(query_embedding, self._loinc_embeddings[concept_id])
            else:
                # Fallback to text matching
                name_lower = concept['concept_name'].lower()
                if query_lower in name_lower:
                    score = 0.7 if name_lower.startswith(query_lower) else 0.5
                elif concept.get('abbreviations'):
                    for abbrev in concept['abbreviations']:
                        if abbrev and query_lower == abbrev.lower():
                            score = 0.9
                            break
                elif concept.get('search_terms'):
                    for term in concept['search_terms']:
                        if term and query_lower in term.lower():
                            score = 0.4
                            break

            if score > 0.3:  # Threshold for relevance
                result = concept.copy()
                result['_score'] = round(score, 4)
                results.append(result)

        # Sort by score descending
        results.sort(key=lambda x: x['_score'], reverse=True)
        return results[:limit]

    def search_population(
        self,
        query: str,
        vocab_type: Optional[str] = None,  # 'conditions' (SNOMED), 'medications' (RxNorm), or None for both
        limit: int = 20,
        use_semantic: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search population vocabulary (SNOMED conditions, RxNorm medications).

        Args:
            query: Search query string
            vocab_type: Filter by type - 'conditions' (SNOMED) or 'medications' (RxNorm)
            limit: Maximum number of results
            use_semantic: Whether to use semantic (embedding) search

        Returns:
            List of matching concepts with similarity scores
        """
        self._load_population()

        if not query or len(query) < 2:
            return []

        # Map vocab_type to vocabulary_id
        vocab_filter = None
        if vocab_type == 'conditions':
            vocab_filter = 'SNOMED'
        elif vocab_type == 'medications':
            vocab_filter = 'RxNorm'

        # Get query embedding
        if use_semantic and self._population_embeddings:
            try:
                query_embedding = self._get_query_embedding(query)
            except Exception:
                use_semantic = False

        results = []
        query_lower = query.lower()

        for concept_id, concept in self._population_concepts.items():
            # Apply vocabulary filter
            if vocab_filter and concept.get('vocabulary_id') != vocab_filter:
                continue

            score = 0.0

            if use_semantic and concept_id in self._population_embeddings:
                score = cosine_similarity(query_embedding, self._population_embeddings[concept_id])
            else:
                # Fallback to text matching
                name_lower = concept['concept_name'].lower()
                if query_lower in name_lower:
                    score = 0.7 if name_lower.startswith(query_lower) else 0.5
                elif concept.get('abbreviations'):
                    for abbrev in concept['abbreviations']:
                        if abbrev and query_lower == abbrev.lower():
                            score = 0.9
                            break
                elif concept.get('search_terms'):
                    for term in concept['search_terms']:
                        if term and query_lower in term.lower():
                            score = 0.4
                            break

            if score > 0.3:
                result = concept.copy()
                result['_score'] = round(score, 4)
                results.append(result)

        results.sort(key=lambda x: x['_score'], reverse=True)
        return results[:limit]

    def get_loinc_by_id(self, concept_id: int) -> Optional[Dict[str, Any]]:
        """Get a LOINC concept by ID."""
        self._load_loinc()
        return self._loinc_concepts.get(concept_id)

    def get_population_by_id(self, concept_id: int) -> Optional[Dict[str, Any]]:
        """Get a population concept by ID."""
        self._load_population()
        return self._population_concepts.get(concept_id)

    def get_loinc_stats(self) -> Dict[str, Any]:
        """Get LOINC vocabulary statistics."""
        self._load_loinc()

        categories = {}
        for concept in self._loinc_concepts.values():
            cat = concept.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1

        return {
            'total_concepts': len(self._loinc_concepts),
            'concepts_with_embeddings': len(self._loinc_embeddings),
            'categories': categories,
        }

    def get_population_stats(self) -> Dict[str, Any]:
        """Get population vocabulary statistics."""
        self._load_population()

        vocabularies = {}
        for concept in self._population_concepts.values():
            vocab = concept.get('vocabulary_id', 'unknown')
            vocabularies[vocab] = vocabularies.get(vocab, 0) + 1

        return {
            'total_concepts': len(self._population_concepts),
            'concepts_with_embeddings': len(self._population_embeddings),
            'vocabularies': vocabularies,
        }


# Singleton instance
_semantic_vocabulary_service: Optional[SemanticVocabularyService] = None


def get_semantic_vocabulary_service() -> SemanticVocabularyService:
    """Get the semantic vocabulary service singleton."""
    global _semantic_vocabulary_service
    if _semantic_vocabulary_service is None:
        _semantic_vocabulary_service = SemanticVocabularyService()
    return _semantic_vocabulary_service
