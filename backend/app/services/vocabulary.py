"""Backward-compatibility shim.

VocabularyService was extracted into the installable ``psdl_vocab`` package
as part of the three-tier architecture refactor. This module re-exports the
package's public API so existing ``from app.services.vocabulary import ...``
call sites keep working unchanged.

New code should import from ``psdl_vocab`` directly.
"""

from psdl_vocab import VocabularyService, get_vocabulary_service

__all__ = ["VocabularyService", "get_vocabulary_service"]
