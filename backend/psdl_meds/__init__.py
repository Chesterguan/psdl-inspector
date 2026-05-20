"""psdl_meds — shared MEDS (Medical Event Data Standard) writer + validator.

Designed to be embedded in both psdl-workbench (live execution) and
psdl-inspector (preview + offline conversion). No DB, no PHI, no
institution-specific code lives in this package.
"""

__version__ = "0.1.0"

from psdl_meds.codes import format_code
from psdl_meds.schema import MEDS_COLUMNS, meds_arrow_schema
from psdl_meds.writer import write_meds_shard

__all__ = [
    "MEDS_COLUMNS",
    "format_code",
    "meds_arrow_schema",
    "write_meds_shard",
]
