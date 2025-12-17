"""Generation endpoints - AI-assisted PSDL scenario creation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import GenerateRequest, GenerateResponse
from app.services.ollama_service import ollama_service
from app.services.openai_service import openai_service
from app.services.validator import validate_scenario

router = APIRouter()


@router.get("/generate/status")
async def generation_status():
    """Check availability of LLM providers.

    Returns availability status for both OpenAI and Ollama.
    """
    ollama_available = await ollama_service.is_available()
    ollama_models = []
    if ollama_available:
        ollama_models = await ollama_service.get_models()

    openai_configured = openai_service.is_configured()

    return {
        "openai": {
            "available": openai_configured,
            "model": openai_service.model if openai_configured else None,
        },
        "ollama": {
            "available": ollama_available,
            "model": ollama_service.model if ollama_available else None,
            "models": ollama_models,
        },
        # Default provider info for backward compatibility
        "available": openai_configured or ollama_available,
        "model": openai_service.model if openai_configured else (ollama_service.model if ollama_available else None),
        "models": ollama_models,  # Keep for Ollama model selector
        "default_provider": "openai" if openai_configured else "ollama",
    }


@router.post("/generate/scenario", response_model=GenerateResponse)
async def generate_scenario(request: GenerateRequest):
    """Generate PSDL scenario from natural language description.

    Uses OpenAI (default) or local Ollama LLM with few-shot prompting to generate
    valid PSDL YAML from a user's clinical scenario description.

    The generated YAML is automatically validated using psdl-lang.
    If validation fails and max_retries > 0, the LLM will attempt
    to correct the errors iteratively.
    """
    provider = request.provider.lower()

    # Validate provider availability
    if provider == "openai":
        if not openai_service.is_configured():
            raise HTTPException(
                status_code=503,
                detail="OpenAI not configured. Set OPENAI_API_KEY environment variable."
            )
    elif provider == "ollama":
        if not await ollama_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="Ollama not available. Start Ollama with: ollama serve"
            )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider: {provider}. Use 'openai' or 'ollama'."
        )

    try:
        # Initial generation
        if provider == "openai":
            generated_yaml = await openai_service.generate_scenario(
                prompt=request.prompt,
                clinical_context=request.clinical_context,
            )
        else:
            generated_yaml = await ollama_service.generate_scenario(
                prompt=request.prompt,
                model=request.model,
                clinical_context=request.clinical_context,
            )

        # Validate the generated YAML
        scenario, errors, warnings = validate_scenario(generated_yaml)
        attempts = 1

        # Self-correction loop
        retry_count = 0
        while len(errors) > 0 and retry_count < request.max_retries:
            retry_count += 1
            attempts += 1

            # Ask LLM to fix the errors
            error_messages = [e.message for e in errors]

            if provider == "openai":
                generated_yaml = await openai_service.correct_scenario(
                    original_yaml=generated_yaml,
                    errors=error_messages,
                    original_prompt=request.prompt,
                )
            else:
                generated_yaml = await ollama_service.correct_scenario(
                    original_yaml=generated_yaml,
                    errors=error_messages,
                    original_prompt=request.prompt,
                    model=request.model,
                )

            # Re-validate
            scenario, errors, warnings = validate_scenario(generated_yaml)

        return GenerateResponse(
            yaml=generated_yaml,
            valid=len(errors) == 0,
            errors=[e.message for e in errors],
            warnings=[w.message for w in warnings],
            attempts=attempts,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
