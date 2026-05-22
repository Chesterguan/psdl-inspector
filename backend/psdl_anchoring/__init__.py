"""psdl_anchoring — terminology anchoring: bind PSDL semantic refs to OMOP vocabulary.

Extracted from psdl-inspector. Uses the Workbench domain-threaded anchor_ref
(ref, psdl_domain, unit) as canonical — domain filtering resolves lab/drug
name collisions (e.g. 'creatinine' → LOINC lab, not RxNorm ingredient).
"""
__version__ = "0.1.0"

from psdl_anchoring.models import TerminologyAnchor, TerminologyAnchors
from psdl_anchoring.service import (
    TerminologyAnchoringService,
    get_terminology_anchoring_service,
)

__all__ = [
    "TerminologyAnchor",
    "TerminologyAnchors",
    "TerminologyAnchoringService",
    "get_terminology_anchoring_service",
]
