"""Backward-compatibility shim — anchoring moved to the psdl_anchoring package."""
from psdl_anchoring import (
    TerminologyAnchor,
    TerminologyAnchors,
    TerminologyAnchoringService,
    get_terminology_anchoring_service,
)

__all__ = [
    "TerminologyAnchor",
    "TerminologyAnchors",
    "TerminologyAnchoringService",
    "get_terminology_anchoring_service",
]
