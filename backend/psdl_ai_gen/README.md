# psdl-ai-gen

OpenAI + Ollama PSDL synthesis services for the PSDL ecosystem.

Extracted from [psdl-inspector](https://github.com/Chesterguan/psdl-inspector).
Provides natural-language → PSDL scenario generation backed by OpenAI GPT-4o or
local Ollama models.

## Installation

```bash
pip install psdl-ai-gen
```

During development (editable install from psdl-inspector backend):

```bash
pip install -e ./psdl_ai_gen
```

## Usage

```python
from psdl_ai_gen import openai_service, ollama_service

# Generate a PSDL scenario via OpenAI
yaml_str = await openai_service.generate_scenario(
    "Detect acute kidney injury using creatinine changes over 48 hours"
)

# Generate via local Ollama
yaml_str = await ollama_service.generate_scenario(
    "Monitor ICU patient deterioration with state transitions"
)
```

## Public API

- `openai_service` — singleton `OpenAIService` instance (GPT-4o-mini, configurable via `OPENAI_API_KEY` env var)
- `ollama_service` — singleton `OllamaService` instance (Mistral-Small, configurable Ollama endpoint)
- `OpenAIService` — class for direct instantiation
- `OllamaService` — class for direct instantiation
