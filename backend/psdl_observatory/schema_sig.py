"""Stable, order-independent schema signature.

A file's identity in the Observatory is (relative_path + schema_signature),
never its filename. The signature hashes the SET of (column, type) pairs so
two files with the same columns in a different order get the same signature.
"""

from __future__ import annotations

import hashlib
from typing import List


def normalize_columns(columns: List[str]) -> List[str]:
    """Lowercase + strip column names (case/whitespace-insensitive identity)."""
    return [c.strip().lower() for c in columns]


def schema_signature(columns: List[str], types: List[str]) -> str:
    """Return a 16-hex-char signature for a schema.

    Order-independent: sorts (normalized_name, type) pairs before hashing, so
    column order does not affect the signature.
    """
    if len(columns) != len(types):
        raise ValueError(
            f"columns and types must have equal length, got {len(columns)} vs {len(types)}"
        )
    norm = normalize_columns(columns)
    pairs = sorted(zip(norm, [str(t) for t in types]))
    blob = "|".join(f"{name}:{typ}" for name, typ in pairs)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
