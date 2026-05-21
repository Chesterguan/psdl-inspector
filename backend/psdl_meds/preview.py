"""Generate synthetic MEDS rows from anchored PSDL signals.

This is the heart of the "Preview MEDS shape" feature — both Workbench
and Inspector use it to render a deterministic, PHI-free 10-row example
of what a scenario's MEDS shard will look like before any real data is
touched.
"""

from datetime import datetime, timedelta
from typing import Iterable, List, Mapping

from psdl_meds.codes import format_code


def synthesize_preview(
    anchors: Iterable[Mapping],
    n: int = 10,
) -> List[dict]:
    """Return `n` synthetic MEDS-shaped rows derived from anchored signals.

    `anchors` is an iterable of dicts with at least `omop_vocabulary` and
    `omop_concept_code` populated; `expected_unit` is consulted to choose
    a plausible synthetic numeric value.

    Synthetic subject IDs are negative ints so they can never collide
    with real OMOP `person_id` values, and synthetic timestamps step by
    one day starting at 2024-01-01.
    """
    anchor_list = [a for a in anchors if a.get("omop_concept_code")]
    if not anchor_list:
        raise ValueError("anchors must contain at least one signal with omop_concept_code")

    base_time = datetime(2024, 1, 1, 8, 0, 0)
    rows: List[dict] = []
    for i in range(n):
        anchor = anchor_list[i % len(anchor_list)]
        rows.append(
            {
                "subject_id": -1000 - (i % 3),  # 3 synthetic subjects, all negative
                "time": base_time + timedelta(days=i),
                "code": format_code(anchor["omop_vocabulary"], anchor["omop_concept_code"]),
                "numeric_value": (
                    1.0 + 0.1 * i if anchor.get("expected_unit") else None
                ),
            }
        )
    return rows
