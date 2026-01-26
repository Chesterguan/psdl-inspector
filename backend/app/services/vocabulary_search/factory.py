"""Factory functions for creating vocabulary search engines.

This module provides easy configuration and instantiation of search engines
with different combinations of embedders, retrievers, and rerankers.

Usage:
    # Use default configuration
    engine = get_vocabulary_search_engine()

    # Use specific configuration
    config = SearchEngineConfig(
        embedder="sapbert",
        retriever="faiss",
        reranker="hybrid",
    )
    engine = create_search_engine(config)

    # Search
    results = engine.search("creatinine", limit=5)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os

from app.services.vocabulary_search.base import (
    VocabularySearchEngine,
    BaseEmbedder,
    BaseRetriever,
    BaseReranker,
)
from app.services.vocabulary_search.embedders import get_embedder, EMBEDDER_REGISTRY
from app.services.vocabulary_search.retrievers import get_retriever, RETRIEVER_REGISTRY
from app.services.vocabulary_search.rerankers import get_reranker, RERANKER_REGISTRY


# Default paths
DEFAULT_VOCAB_DIR = Path(__file__).parent.parent.parent.parent / "data" / "vocabulary" / "enriched"
DEFAULT_CACHE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "vocabulary" / "embeddings"


@dataclass
class SearchEngineConfig:
    """Configuration for vocabulary search engine.

    Attributes:
        embedder: Name of embedder to use (minilm, sapbert, biolord, openai)
        retriever: Name of retriever to use (faiss, numpy, hnsw)
        reranker: Name of reranker to use (none, rules, string, hybrid)
        vocab_path: Path to vocabulary JSON file
        cache_dir: Directory for caching embeddings and indices
    """
    embedder: str = "minilm"
    retriever: str = "faiss"
    reranker: str = "rules"
    vocab_path: Optional[str] = None
    cache_dir: Optional[str] = None

    def __post_init__(self):
        # Set default paths
        if self.vocab_path is None:
            vocab_file = DEFAULT_VOCAB_DIR / "vocabulary_final.json"
            if not vocab_file.exists():
                vocab_file = DEFAULT_VOCAB_DIR / "vocabulary_partial.json"
            self.vocab_path = str(vocab_file)

        if self.cache_dir is None:
            self.cache_dir = str(DEFAULT_CACHE_DIR)

    @classmethod
    def from_env(cls) -> "SearchEngineConfig":
        """Create config from environment variables.

        Environment variables:
        - VOCAB_SEARCH_EMBEDDER: minilm, sapbert, biolord, openai
        - VOCAB_SEARCH_RETRIEVER: faiss, numpy, hnsw
        - VOCAB_SEARCH_RERANKER: none, rules, string, hybrid
        - VOCAB_SEARCH_VOCAB_PATH: Path to vocabulary file
        - VOCAB_SEARCH_CACHE_DIR: Cache directory
        """
        return cls(
            embedder=os.environ.get("VOCAB_SEARCH_EMBEDDER", "minilm"),
            retriever=os.environ.get("VOCAB_SEARCH_RETRIEVER", "faiss"),
            reranker=os.environ.get("VOCAB_SEARCH_RERANKER", "rules"),
            vocab_path=os.environ.get("VOCAB_SEARCH_VOCAB_PATH"),
            cache_dir=os.environ.get("VOCAB_SEARCH_CACHE_DIR"),
        )

    @classmethod
    def default(cls) -> "SearchEngineConfig":
        """Default configuration (fast, good quality)."""
        return cls(embedder="minilm", retriever="faiss", reranker="rules")

    @classmethod
    def medical_optimized(cls) -> "SearchEngineConfig":
        """Configuration optimized for medical concept matching."""
        return cls(embedder="sapbert", retriever="faiss", reranker="hybrid")

    @classmethod
    def high_quality(cls) -> "SearchEngineConfig":
        """Highest quality configuration (slower)."""
        return cls(embedder="biolord", retriever="faiss", reranker="hybrid")


def create_search_engine(config: SearchEngineConfig) -> VocabularySearchEngine:
    """Create a search engine with the given configuration.

    Args:
        config: SearchEngineConfig specifying components to use

    Returns:
        Configured VocabularySearchEngine instance
    """
    embedder = get_embedder(config.embedder)
    retriever = get_retriever(config.retriever)
    reranker = get_reranker(config.reranker)

    return VocabularySearchEngine(
        embedder=embedder,
        retriever=retriever,
        reranker=reranker,
        vocab_path=config.vocab_path,
        cache_dir=config.cache_dir,
    )


# Singleton instance
_default_engine: Optional[VocabularySearchEngine] = None
_current_config: Optional[SearchEngineConfig] = None


def get_vocabulary_search_engine(config: Optional[SearchEngineConfig] = None) -> VocabularySearchEngine:
    """Get vocabulary search engine singleton.

    Args:
        config: Optional config. If provided and different from current,
                a new engine is created.

    Returns:
        VocabularySearchEngine instance
    """
    global _default_engine, _current_config

    # Use environment-based config if none provided
    if config is None:
        config = SearchEngineConfig.from_env()

    # Check if we need to create a new engine
    if _default_engine is None or _current_config != config:
        _default_engine = create_search_engine(config)
        _current_config = config

    return _default_engine


def reset_engine() -> None:
    """Reset the singleton engine. Useful for testing or config changes."""
    global _default_engine, _current_config
    _default_engine = None
    _current_config = None


def list_available_components() -> dict:
    """List all available components for configuration."""
    return {
        "embedders": list(EMBEDDER_REGISTRY.keys()),
        "retrievers": list(RETRIEVER_REGISTRY.keys()),
        "rerankers": list(RERANKER_REGISTRY.keys()),
    }
