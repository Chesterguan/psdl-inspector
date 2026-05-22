"""Backward-compatibility shim — re-exports from psdl_vocab_search.factory."""
from psdl_vocab_search.factory import *  # noqa: F401,F403
from psdl_vocab_search.factory import (  # noqa: F401
    SearchEngineConfig,
    create_search_engine,
    get_vocabulary_search_engine,
    reset_engine,
    list_available_components,
)
