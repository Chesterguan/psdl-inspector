"""Backward-compatibility shim.

ollama_service was extracted into the psdl_ai_gen package. This re-exports
its public API so existing `from app.services.ollama_service import ollama_service`
call sites keep working.
"""
from psdl_ai_gen.ollama_service import OllamaService, ollama_service  # noqa: F401

__all__ = ["OllamaService", "ollama_service"]
