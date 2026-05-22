"""Backward-compatibility shim — re-exports from psdl_vocab_search.embedders."""
from psdl_vocab_search.embedders import *  # noqa: F401,F403
from psdl_vocab_search.embedders import (  # noqa: F401
    SentenceTransformerEmbedder,
    SapBERTEmbedder,
    BioLORDEmbedder,
    OpenAIEmbedder,
    EMBEDDER_REGISTRY,
    get_embedder,
)
