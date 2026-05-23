"""psdl_vocab — enriched OMOP vocabulary + searchable service.

Extracted from psdl-inspector for shared use across the PSDL ecosystem.
Both psdl-inspector and psdl-workbench consume this package. The vocab JSON
is NOT bundled in the wheel; it is downloaded from a GitHub Release asset and
cached on first use (override with PSDL_VOCAB_DATA_DIR for offline installs).
See _data_loader.py for the full resolution order.
"""

__version__ = "0.1.0"

from psdl_vocab.service import VocabularyService, get_vocabulary_service

__all__ = ["VocabularyService", "get_vocabulary_service"]
