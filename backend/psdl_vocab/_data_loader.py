"""Resolve the directory containing vocabulary_final.json.

Default: bundled data at psdl_vocab/data/. Override with the
PSDL_VOCAB_DATA_DIR env var to point at a custom vocab build (e.g.
developing a new vocab without reinstalling the package).
"""

import os
from importlib import resources
from importlib.abc import Traversable
from pathlib import Path
from typing import Union


def get_vocab_data_path() -> Union[Path, Traversable]:
    """Return the directory containing vocabulary_final.json.

    Returns a pathlib.Path when PSDL_VOCAB_DATA_DIR is set, otherwise a
    Traversable handle to the bundled package data. Both support the
    ``dir / "vocabulary_final.json"`` join, ``.exists()``, and ``open()``
    used by VocabularyService, so callers should not assume pathlib-only
    methods (.parent, .stem, etc.).
    """
    override = os.environ.get("PSDL_VOCAB_DATA_DIR")
    if override:
        p = Path(override)
        if not p.is_dir():
            raise RuntimeError(
                f"PSDL_VOCAB_DATA_DIR={override} is not a directory"
            )
        return p
    return resources.files("psdl_vocab") / "data"
