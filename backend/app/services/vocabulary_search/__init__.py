"""Backward-compatibility shim.

The modular vocabulary search engine was extracted into the
psdl_vocab_search package. This re-exports its public API so existing
``from app.services.vocabulary_search import ...`` call sites keep working.
"""
from psdl_vocab_search import (  # noqa: F401
    VocabularySearchResult,
    BaseEmbedder,
    BaseRetriever,
    BaseReranker,
    VocabularySearchEngine,
    get_vocabulary_search_engine,
    create_search_engine,
    SearchEngineConfig,
    list_available_components,
    reset_engine,
)
