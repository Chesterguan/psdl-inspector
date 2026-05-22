"""psdl_vocab — enriched OMOP vocabulary + searchable service.

Extracted from psdl-inspector for shared use across the PSDL ecosystem.
Both psdl-inspector and psdl-workbench consume this package; the
vocab JSON ships bundled with the wheel (override with PSDL_VOCAB_DATA_DIR).
"""

__version__ = "0.1.0"

from psdl_vocab.service import VocabularyService, get_vocabulary_service

__all__ = ["VocabularyService", "get_vocabulary_service"]
