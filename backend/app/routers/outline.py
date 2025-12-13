"""Outline endpoint - Inspector's visualization of psdl-lang IR."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import OutlineRequest, OutlineResponse
from app.services.parser import parse_scenario, ParseError
from app.services.outliner import generate_outline

router = APIRouter()


@router.post("/outline", response_model=OutlineResponse)
async def outline(request: OutlineRequest) -> OutlineResponse:
    """Generate a semantic outline from a PSDL scenario.

    Uses psdl-lang for parsing, then transforms the IR into
    a visualization-friendly format with dependency tracking.
    """
    try:
        scenario = parse_scenario(request.content)
    except ParseError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return generate_outline(scenario)
