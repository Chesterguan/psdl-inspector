"""Backward-compatibility shim.

openai_service was extracted into the psdl_ai_gen package. This re-exports
its public API so existing `from app.services.openai_service import openai_service`
call sites keep working.
"""
from psdl_ai_gen.openai_service import OpenAIService, openai_service  # noqa: F401

__all__ = ["OpenAIService", "openai_service"]
