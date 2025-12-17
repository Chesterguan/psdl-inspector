"""Export endpoints - Inspector's certified bundle generation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

from app.models.schemas import ExportRequest, CertifiedBundle, IRBExportRequest
from app.services.parser import parse_scenario, ParseError
from app.services.validator import validate_scenario
from app.services.exporter import generate_certified_bundle
from app.services.docx_exporter import generate_irb_document

router = APIRouter()


@router.post("/export/bundle", response_model=CertifiedBundle)
async def export_bundle(request: ExportRequest) -> CertifiedBundle:
    """Export a Certified Audit Bundle from a PSDL scenario.

    This is Inspector's core value for governance:
    - Full checksum for integrity verification
    - Validation results with psdl-lang version
    - Audit information (intent, rationale, provenance)
    - Human-readable summary for IRB/admin review
    """
    # First validate
    scenario, errors, warnings = validate_scenario(request.content)

    if errors:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot certify invalid scenario: {errors[0].message if errors else 'Unknown error'}"
        )

    # Generate certified bundle with full context
    return generate_certified_bundle(
        scenario=scenario,
        raw_yaml=request.content,
        format=request.format,
        intent=request.intent,
        rationale=request.rationale,
        provenance=request.provenance,
        errors=[],  # Already validated as valid
        warnings=[e.model_dump() for e in warnings],
    )


@router.post("/export/download")
async def export_download(request: ExportRequest):
    """Export certified bundle as a downloadable JSON file."""
    # First validate
    scenario, errors, warnings = validate_scenario(request.content)

    if errors:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot certify invalid scenario: {errors[0].message if errors else 'Unknown error'}"
        )

    bundle = generate_certified_bundle(
        scenario=scenario,
        raw_yaml=request.content,
        format=request.format,
        intent=request.intent,
        rationale=request.rationale,
        provenance=request.provenance,
        errors=[],
        warnings=[e.model_dump() for e in warnings],
    )

    filename = f"{scenario.name}_certified_bundle.json"

    return JSONResponse(
        content=bundle.model_dump(),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/export/draft", response_model=CertifiedBundle)
async def export_draft(request: ExportRequest) -> CertifiedBundle:
    """Export a draft bundle even if validation fails.

    Use this for work-in-progress scenarios that aren't ready for certification.
    The bundle will include validation errors.
    """
    # Validate but don't require success
    scenario, errors, warnings = validate_scenario(request.content)

    # If scenario is None (parse failed), try to parse again for better error
    if scenario is None:
        try:
            scenario = parse_scenario(request.content)
        except ParseError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot parse scenario: {e.message}"
            )

    # Generate bundle with validation errors included
    return generate_certified_bundle(
        scenario=scenario,
        raw_yaml=request.content,
        format=request.format,
        intent=request.intent,
        rationale=request.rationale,
        provenance=request.provenance,
        errors=[e.model_dump() for e in errors],
        warnings=[e.model_dump() for e in warnings],
    )


@router.post("/export/irb-document")
async def export_irb_document(request: IRBExportRequest):
    """Export Word document for IRB preparation with AI enrichment.

    Generates an editable .docx file containing:
    - AI-enriched executive summary and clinical background
    - Algorithm overview (auto-derived from PSDL)
    - Data elements required with narrative explanation
    - Trend and logic definitions
    - Clinical workflow integration
    - Safety considerations and limitations
    - Recommendation for IRB review
    - Technical appendix
    """
    import psdl
    from app.services.openai_service import openai_service

    # Parse the scenario
    try:
        scenario = parse_scenario(request.content)
    except ParseError as e:
        raise HTTPException(status_code=400, detail=f"Cannot parse scenario: {e.message}")

    # Build scenario info for document
    scenario_info = {
        'name': scenario.name,
        'version': scenario.version,
        'description': scenario.description,
        'psdl_lang_version': psdl.__version__,
        'signals': [
            {
                'name': name,
                'ref': sig.ref,
                'unit': sig.unit,
                'concept_id': sig.concept_id,
                'description': getattr(sig, 'description', None),
            }
            for name, sig in scenario.signals.items()
        ],
        'trends': [
            {
                'name': name,
                'expr': trend.raw_expr,
                'description': trend.description,
            }
            for name, trend in scenario.trends.items()
        ],
        'logic': [
            {
                'name': name,
                'expr': logic.expr,
                'severity': logic.severity.value if logic.severity else None,
                'description': logic.description,
            }
            for name, logic in scenario.logic.items()
        ],
    }

    # Build governance data for document
    governance_data = {
        'clinical_summary': request.governance.clinical_summary,
        'justification': request.governance.justification,
        'risk_assessment': request.governance.risk_assessment,
    }

    # Try to enrich with AI if OpenAI is configured
    enriched_content = None
    if openai_service.is_configured():
        try:
            enriched_content = await openai_service.enrich_irb_document(
                scenario_info, governance_data
            )
            # Check if enrichment had an error
            if enriched_content and enriched_content.get('error'):
                enriched_content = None  # Fall back to basic document
        except Exception:
            enriched_content = None  # Fall back to basic document on any error

    # Generate Word document
    doc_bytes = generate_irb_document(scenario_info, governance_data, enriched_content)

    filename = f"{scenario.name}_IRB_Documentation.docx"

    return Response(
        content=doc_bytes,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )
