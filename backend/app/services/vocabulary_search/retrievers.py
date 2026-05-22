"""Backward-compatibility shim — re-exports from psdl_vocab_search.retrievers."""
from psdl_vocab_search.retrievers import *  # noqa: F401,F403
from psdl_vocab_search.retrievers import (  # noqa: F401
    FAISSRetriever,
    NumpyRetriever,
    HNSWRetriever,
    RETRIEVER_REGISTRY,
    get_retriever,
)
