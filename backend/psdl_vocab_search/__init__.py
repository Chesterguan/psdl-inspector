"""Modular vocabulary search system.

This module provides a pluggable architecture for vocabulary concept matching:
- Embedders: Convert text to vectors (MiniLM, SapBERT, BioLORD, OpenAI, etc.)
- Retrievers: Find similar vectors (FAISS, Annoy, ChromaDB, etc.)
- Rerankers: Adjust scores based on domain knowledge

To swap implementations, modify the factory functions or config.
"""

from psdl_vocab_search.base import (
    VocabularySearchResult,
    BaseEmbedder,
    BaseRetriever,
    BaseReranker,
    VocabularySearchEngine,
)
from psdl_vocab_search.factory import (
    get_vocabulary_search_engine,
    create_search_engine,
    SearchEngineConfig,
    list_available_components,
    reset_engine,
)

__all__ = [
    "VocabularySearchResult",
    "BaseEmbedder",
    "BaseRetriever",
    "BaseReranker",
    "VocabularySearchEngine",
    "get_vocabulary_search_engine",
    "create_search_engine",
    "SearchEngineConfig",
    "list_available_components",
    "reset_engine",
]
