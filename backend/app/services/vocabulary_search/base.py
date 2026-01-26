"""Base classes and interfaces for vocabulary search components.

This module defines the abstract interfaces that allow swapping implementations:
- BaseEmbedder: Text → Vector
- BaseRetriever: Vector → Candidates
- BaseReranker: Candidates → Ranked Results

Each component can be implemented independently and combined freely.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Protocol
import numpy as np


@dataclass
class VocabularySearchResult:
    """A single search result with scores and metadata."""
    concept_id: int
    concept_name: str
    concept_code: Optional[str] = None
    vocabulary_id: Optional[str] = None
    domain_id: Optional[str] = None

    # Scores
    raw_score: float = 0.0  # Original retrieval score
    final_score: float = 0.0  # After reranking

    # Additional metadata from concept
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "concept_id": self.concept_id,
            "concept_name": self.concept_name,
            "concept_code": self.concept_code,
            "vocabulary_id": self.vocabulary_id,
            "domain_id": self.domain_id,
            "_raw_score": self.raw_score,
            "_score": self.final_score,
            **self.metadata,
        }


class BaseEmbedder(ABC):
    """Abstract base class for text embedding.

    Implementations:
    - SentenceTransformerEmbedder: Uses sentence-transformers (MiniLM, SapBERT, BioLORD)
    - OpenAIEmbedder: Uses OpenAI embeddings API
    - HuggingFaceEmbedder: Uses transformers directly (for SapBERT CLS extraction)
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier for cache invalidation."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass

    @abstractmethod
    def embed(self, texts: List[str]) -> np.ndarray:
        """Embed a list of texts.

        Args:
            texts: List of strings to embed

        Returns:
            numpy array of shape (len(texts), dimension)
        """
        pass

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query. Override for query-specific handling."""
        return self.embed([query])[0]


class BaseRetriever(ABC):
    """Abstract base class for vector retrieval.

    Implementations:
    - FAISSRetriever: Uses FAISS for fast similarity search
    - AnnoyRetriever: Uses Annoy (Spotify's library)
    - ChromaRetriever: Uses ChromaDB
    - SimpleRetriever: Brute-force numpy (for small vocabularies)
    """

    @abstractmethod
    def build_index(self, embeddings: np.ndarray, concept_ids: List[int]) -> None:
        """Build the retrieval index.

        Args:
            embeddings: numpy array of shape (n_concepts, dimension)
            concept_ids: List of concept IDs corresponding to each embedding
        """
        pass

    @abstractmethod
    def search(self, query_embedding: np.ndarray, k: int) -> List[tuple[int, float]]:
        """Search for similar vectors.

        Args:
            query_embedding: Query vector of shape (dimension,)
            k: Number of results to return

        Returns:
            List of (concept_id, score) tuples, sorted by score descending
        """
        pass

    @abstractmethod
    def save(self, path: str) -> None:
        """Save index to disk."""
        pass

    @abstractmethod
    def load(self, path: str) -> bool:
        """Load index from disk. Returns True if successful."""
        pass


class BaseReranker(ABC):
    """Abstract base class for result reranking.

    Implementations:
    - RuleBasedReranker: Uses domain rules (current implementation)
    - StringSimilarityReranker: Combines with Jaccard/Levenshtein
    - LLMReranker: Uses LLM to verify/rerank candidates
    - HybridReranker: Combines multiple rerankers
    """

    @abstractmethod
    def rerank(
        self,
        query: str,
        candidates: List[VocabularySearchResult],
        concepts_data: Dict[int, Dict[str, Any]],
    ) -> List[VocabularySearchResult]:
        """Rerank candidates based on query and concept data.

        Args:
            query: Original search query
            candidates: List of candidates with raw_score set
            concepts_data: Dict mapping concept_id to full concept data

        Returns:
            Reranked list with final_score set
        """
        pass


class VocabularySearchEngine:
    """Main search engine that orchestrates embedder, retriever, and reranker.

    This class combines the three components and handles:
    - Vocabulary loading
    - Index building/caching
    - Search orchestration
    """

    def __init__(
        self,
        embedder: BaseEmbedder,
        retriever: BaseRetriever,
        reranker: BaseReranker,
        vocab_path: str,
        cache_dir: str,
    ):
        self.embedder = embedder
        self.retriever = retriever
        self.reranker = reranker
        self.vocab_path = vocab_path
        self.cache_dir = cache_dir

        self._concepts: List[Dict[str, Any]] = []
        self._concepts_by_id: Dict[int, Dict[str, Any]] = {}
        self._loaded = False

    def _get_concept_text(self, concept: Dict[str, Any]) -> str:
        """Build text representation for embedding.

        Override this method to customize how concepts are converted to text.
        """
        name = concept["concept_name"]

        # Extract core name without modifiers
        core_name = name.split("[")[0].strip()
        if " --" in name:
            base_part = name.split(" --")[0]
        else:
            base_part = name

        parts = [core_name, base_part]

        # Add abbreviations
        if concept.get("abbreviations"):
            parts.extend(concept["abbreviations"][:3])

        return " ".join(filter(None, set(parts)))

    def load(self) -> None:
        """Load vocabulary and build/load index."""
        if self._loaded:
            return

        import json
        from pathlib import Path

        # Load vocabulary
        vocab_file = Path(self.vocab_path)
        if not vocab_file.exists():
            raise FileNotFoundError(f"Vocabulary file not found: {self.vocab_path}")

        with open(vocab_file) as f:
            self._concepts = json.load(f)

        # Build lookup
        self._concepts_by_id = {c["concept_id"]: c for c in self._concepts}

        # Try to load cached index
        cache_path = Path(self.cache_dir)
        index_file = cache_path / f"index_{self.embedder.model_name.replace('/', '_')}.bin"
        meta_file = cache_path / f"meta_{self.embedder.model_name.replace('/', '_')}.json"

        if index_file.exists() and meta_file.exists():
            with open(meta_file) as f:
                meta = json.load(f)

            if (meta.get("model") == self.embedder.model_name and
                meta.get("num_concepts") == len(self._concepts)):
                if self.retriever.load(str(index_file)):
                    self._loaded = True
                    return

        # Build index
        self._build_index()
        self._loaded = True

    def _build_index(self) -> None:
        """Build embeddings and retrieval index."""
        import json
        from pathlib import Path

        print(f"Building index with {self.embedder.model_name}...")

        # Generate texts
        texts = [self._get_concept_text(c) for c in self._concepts]

        # Embed
        embeddings = self.embedder.embed(texts)

        # Normalize for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms

        # Build retriever index
        concept_ids = [c["concept_id"] for c in self._concepts]
        self.retriever.build_index(embeddings, concept_ids)

        # Save
        cache_path = Path(self.cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)

        index_file = cache_path / f"index_{self.embedder.model_name.replace('/', '_')}.bin"
        meta_file = cache_path / f"meta_{self.embedder.model_name.replace('/', '_')}.json"

        self.retriever.save(str(index_file))

        with open(meta_file, 'w') as f:
            json.dump({
                "model": self.embedder.model_name,
                "num_concepts": len(self._concepts),
            }, f)

        print(f"Index saved to {cache_path}")

    def search(self, query: str, limit: int = 10) -> List[VocabularySearchResult]:
        """Search for concepts matching the query.

        Args:
            query: Search query (e.g., "creatinine", "heart rate")
            limit: Maximum number of results

        Returns:
            List of VocabularySearchResult, sorted by final_score
        """
        self.load()

        # Embed query
        query_embedding = self.embedder.embed_query(query)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)

        # Retrieve candidates (get more for reranking)
        num_candidates = min(limit * 20, 200)
        raw_results = self.retriever.search(query_embedding, num_candidates)

        # Convert to VocabularySearchResult
        candidates = []
        for concept_id, score in raw_results:
            concept = self._concepts_by_id.get(concept_id)
            if concept:
                candidates.append(VocabularySearchResult(
                    concept_id=concept_id,
                    concept_name=concept["concept_name"],
                    concept_code=concept.get("concept_code"),
                    vocabulary_id=concept.get("vocabulary_id"),
                    domain_id=concept.get("domain_id"),
                    raw_score=score,
                    metadata={
                        "abbreviations": concept.get("abbreviations"),
                        "search_terms": concept.get("search_terms"),
                        "typical_units": concept.get("typical_units"),
                    }
                ))

        # Rerank
        reranked = self.reranker.rerank(query, candidates, self._concepts_by_id)

        return reranked[:limit]

    def get_by_id(self, concept_id: int) -> Optional[Dict[str, Any]]:
        """Get concept by ID."""
        self.load()
        return self._concepts_by_id.get(concept_id)
