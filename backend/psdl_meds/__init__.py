"""psdl_meds — shared MEDS (Medical Event Data Standard) writer + validator.

Designed to be embedded in both psdl-workbench (live execution) and
psdl-inspector (preview + offline conversion). No DB, no PHI, no
institution-specific code lives in this package.
"""

__version__ = "0.1.0"

from psdl_meds.codes import format_code

__all__ = [
    "format_code",
]
