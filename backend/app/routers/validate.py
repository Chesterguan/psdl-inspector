"""Validation endpoint - wraps psdl-lang validation for API."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import ValidationRequest, ValidationResponse
from app.services.validator import validate_scenario
from app.services.parser import scenario_to_dict

router = APIRouter()


@router.post("/validate", response_model=ValidationResponse)
async def validate(request: ValidationRequest) -> ValidationResponse:
    """Validate a PSDL scenario.

    Delegates to psdl-lang for all semantic validation.
    Inspector adds UX hints (unused signals/trends) as warnings.

    Returns validation result with errors and warnings.
    """
    scenario, errors, warnings = validate_scenario(request.content)

    # Convert scenario to dict if valid
    parsed = scenario_to_dict(scenario) if scenario else None

    return ValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        parsed=parsed,
    )
