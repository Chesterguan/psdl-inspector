"""psdl_ai_gen — OpenAI + Ollama PSDL synthesis for the PSDL ecosystem.

Extracted from psdl-inspector. Provides natural-language → PSDL scenario
generation backed by OpenAI or local Ollama.
"""

__version__ = "0.1.0"

from psdl_ai_gen.openai_service import OpenAIService, openai_service
from psdl_ai_gen.ollama_service import OllamaService, ollama_service

__all__ = [
    "OpenAIService",
    "openai_service",
    "OllamaService",
    "ollama_service",
]
