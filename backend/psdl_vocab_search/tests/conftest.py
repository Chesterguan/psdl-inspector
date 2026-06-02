"""Skip guard for integration tests that require the BioLORD v2 index.

Integration tests are skipped unless one of the following conditions is met:
1. PSDL_RUN_INTEGRATION=1 is set in the environment (explicit opt-in).
2. PSDL_VOCAB_SEARCH_DATA_DIR is set (offline override pointing to a local index dir).
3. The BioLORD v2 cache exists at the default cache location
   (~/.cache/psdl_vocab_search/v2-biolord/ or PSDL_VOCAB_SEARCH_CACHE_DIR).

This mirrors the psdl_vocab conftest pattern so unit test runs stay fast and
network-free.  The integration guard is applied via pytest_collection_modifyitems
so the skip reason is visible in the collected output.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Required files for the pre-built index (must match _index_loader.REQUIRED_FILES).
_REQUIRED_FILES = ("index.faiss", "index.faiss.meta", "metadata.json")


def _index_available() -> bool:
    """Return True if the BioLORD v2 index is accessible without a download."""
    # 1. Explicit env override.
    if os.environ.get("PSDL_VOCAB_SEARCH_DATA_DIR"):
        return True

    # 2. Custom cache dir override.
    cache_override = os.environ.get("PSDL_VOCAB_SEARCH_CACHE_DIR")
    if cache_override:
        d = Path(cache_override)
        return all((d / f).exists() for f in _REQUIRED_FILES)

    # 3. Default cache location.
    default = Path.home() / ".cache" / "psdl_vocab_search" / "v2-biolord"
    return all((default / f).exists() for f in _REQUIRED_FILES)


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless opt-in or index already cached."""
    run_integration = os.environ.get("PSDL_RUN_INTEGRATION", "").strip() == "1"
    index_cached = _index_available()

    if run_integration or index_cached:
        return  # Let all tests run — don't add any skip markers.

    skip_marker = pytest.mark.skip(
        reason=(
            "Integration test skipped: BioLORD v2 index not cached and "
            "PSDL_RUN_INTEGRATION is not set. "
            "Run with PSDL_RUN_INTEGRATION=1 to trigger a first-use download (~1.7 GB), "
            "or set PSDL_VOCAB_SEARCH_DATA_DIR to a local index directory."
        )
    )
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(skip_marker)
