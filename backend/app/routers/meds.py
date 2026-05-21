"""MEDS Preview endpoint for psdl-inspector.

Single endpoint: synthesize a preview MEDS shard from anchored signals,
write it to a tempfile, validate it against the MEDS spec, and return a
summary including the codes the preview used.

No DB, no auth — Inspector is single-tenant OSS.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from psdl_meds.preview import synthesize_preview
from psdl_meds.validator import validate_shard
from psdl_meds.writer import write_meds_shard

router = APIRouter()

_PREVIEW_DIR = Path(
    os.environ.get(
        "PSDL_INSPECTOR_MEDS_DIR",
        str(Path(tempfile.gettempdir()) / "psdl_inspector_meds"),
    )
)


class MedsAnchor(BaseModel):
    psdl_signal: str
    omop_vocabulary: str
    omop_concept_code: str
    expected_unit: Optional[str] = None


class MedsPreviewRequest(BaseModel):
    anchors: List[MedsAnchor]
    n: int = 10


class MedsPreviewResponse(BaseModel):
    n_events: int
    n_subjects: int
    path: str
    codes_used: List[str]


@router.post("/meds/preview", response_model=MedsPreviewResponse)
def preview_meds(request: MedsPreviewRequest) -> MedsPreviewResponse:
    """Synthesize a PHI-free MEDS preview shard from anchored PSDL signals."""
    if not request.anchors:
        raise HTTPException(status_code=400, detail="anchors must not be empty")

    _PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _PREVIEW_DIR / "preview.parquet"

    def _dump(a: MedsAnchor) -> dict:
        return a.model_dump() if hasattr(a, "model_dump") else a.dict()

    rows = synthesize_preview(
        [_dump(a) for a in request.anchors],
        n=request.n,
    )
    summary = write_meds_shard(rows, out_path)
    validate_shard(out_path)

    return MedsPreviewResponse(
        n_events=summary["n_events"],
        n_subjects=summary["n_subjects"],
        path=str(out_path),
        codes_used=sorted({r["code"] for r in rows}),
    )
