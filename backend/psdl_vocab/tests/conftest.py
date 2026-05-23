"""Make the psdl_vocab smoke tests network-free.

The vocab data no longer ships in the wheel — at runtime ``_data_loader``
downloads it from a GitHub Release and caches it. Tests must NOT depend on a
live download (CI runs offline). This conftest guarantees the data is present
locally BEFORE any test runs, via this resolution order:

1. ``PSDL_VOCAB_DATA_DIR`` already set         -> trust it, do nothing.
2. The download cache is already warm          -> trust it, do nothing.
3. A local source JSON is discoverable         -> copy it into the cache and
   point ``PSDL_VOCAB_DATA_DIR`` at that cache (no network).

Source JSON discovery (step 3) checks, in order:
- ``PSDL_VOCAB_TEST_SRC`` env var (path to a vocabulary_final.json), then
- the standard download cache (``~/.cache/psdl_vocab/v1/`` or
  ``PSDL_VOCAB_CACHE_DIR``).

If none of the above yields data, the tests fall through to the normal loader
(which would download). That keeps a developer's first local run working while
keeping CI offline — CI should pre-warm the cache or set PSDL_VOCAB_DATA_DIR.
"""

import os
import shutil
from pathlib import Path

VOCAB_FILENAME = "vocabulary_final.json"


def _cache_dir() -> Path:
    override = os.environ.get("PSDL_VOCAB_CACHE_DIR")
    if override:
        return Path(override)
    return Path.home() / ".cache" / "psdl_vocab" / "v1"


def _ensure_offline_vocab() -> None:
    # 1. Explicit override already in place — respect it, no network.
    if os.environ.get("PSDL_VOCAB_DATA_DIR"):
        return

    cache_dir = _cache_dir()
    cached = cache_dir / VOCAB_FILENAME

    # 2. Cache already warm — pin the override to it so the loader never
    #    even considers the network during the test session.
    if cached.exists():
        os.environ["PSDL_VOCAB_DATA_DIR"] = str(cache_dir)
        return

    # 3. Try to warm the cache from a discoverable local source copy.
    src = os.environ.get("PSDL_VOCAB_TEST_SRC")
    candidates = [Path(src)] if src else []
    if candidates:
        for cand in candidates:
            if cand.is_file():
                cache_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(cand, cached)
                os.environ["PSDL_VOCAB_DATA_DIR"] = str(cache_dir)
                return

    # 4. Nothing local found. Leave the env unset; the loader will download
    #    on first use (acceptable for a developer's initial local run, but CI
    #    should pre-warm the cache or set PSDL_VOCAB_DATA_DIR to stay offline).


_ensure_offline_vocab()
