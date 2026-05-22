"""Backward-compatibility shim — re-exports from psdl_vocab_search.base."""
from psdl_vocab_search.base import *  # noqa: F401,F403
from psdl_vocab_search.base import (  # noqa: F401
    VocabularySearchResult,
    BaseEmbedder,
    BaseRetriever,
    BaseReranker,
    VocabularySearchEngine,
)
