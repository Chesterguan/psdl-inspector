"""Export endpoints - Inspector's audit bundle generation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.models.schemas import ExportRequest, ExportResponse
from app.services.parser import parse_scenario, ParseError
from app.services.exporter import generate_audit_bundle

router = APIRouter()


@router.post("/export/bundle", response_model=ExportResponse)
async def export_bundle(request: ExportRequest) -> ExportResponse:
    """Export an audit bundle from a PSDL scenario.

    This is Inspector's value-add for governance:
    - Metadata (timestamp, checksum)
    - Full parsed scenario
    - Audit information
    - Human-readable summary for IRB/admin review
    """
    try:
        scenario = parse_scenario(request.content)
    except ParseError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return generate_audit_bundle(scenario, request.format)


@router.post("/export/download")
async def export_download(request: ExportRequest):
    """Export audit bundle as a downloadable file."""
    try:
        scenario = parse_scenario(request.content)
    except ParseError as e:
        raise HTTPException(status_code=400, detail=e.message)

    bundle = generate_audit_bundle(scenario, request.format)
    filename = f"{scenario.name}_audit_bundle.json"

    return JSONResponse(
        content=bundle.model_dump(),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
