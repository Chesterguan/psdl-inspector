"""Structural column-role inference for the EDW semantic registry.

Roles describe the STRUCTURAL semantics of a column (is it a patient
identifier? a timestamp? free text?) — NOT clinical concept mapping (that is
M1 auto-mapping / FAISS, a separate problem). Inference is heuristic and based
on real column names, never hardcoded table assumptions.

ROLE_PATTERNS is intentionally a plain, ordered data structure so the community
can PR additional patterns without touching logic. First matching role wins
(precedence matters — see the ordering rationale inline).
"""

from __future__ import annotations

import re
from typing import List, Tuple

ROLE_PATIENT = "patient"
ROLE_ENCOUNTER = "encounter"
ROLE_CODE = "code"
ROLE_TIME = "time"
ROLE_OUTCOME = "outcome"
ROLE_TEXT = "text"
ROLE_OTHER = "other"

ALL_ROLES = (
    ROLE_PATIENT, ROLE_ENCOUNTER, ROLE_CODE, ROLE_TIME,
    ROLE_OUTCOME, ROLE_TEXT, ROLE_OTHER,
)


def normalize_col(name: str) -> str:
    """Normalize a column name: lowercase, split camelCase, unify separators.

    'encounterID' -> 'encounter_id'; 'Visit-Occurrence-ID' -> 'visit_occurrence_id';
    'note__text' -> 'note_text'.
    """
    # split camelCase / PascalCase boundaries: aB -> a_B, and ABc -> A_Bc
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name.strip())
    s = s.lower()
    # any run of non-alphanumeric becomes a single underscore
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


# Ordered (role, [regex]) pairs. FIRST match wins. Ordering rationale:
#   patient/encounter ID columns first (they often contain tokens that would
#   otherwise match weaker patterns); code before time so '*_code' is code;
#   time before outcome so '*_date'/'*_time' is a timestamp even when the stem
#   is clinically an outcome (e.g. 'death_date' is a time, 'death_flag' is an
#   outcome); text last among the named roles.
ROLE_PATTERNS: List[Tuple[str, List[str]]] = [
    (ROLE_PATIENT, [
        r"^(patient|person|subject|member|pat)_?(id|key|num|identifier|sk)$",
        r"^mrn$", r"^pat_?id$",
    ]),
    (ROLE_ENCOUNTER, [
        r"^(encounter|visit|admission|hospitalization|hadm|stay|episode|enc)_?"
        r"(id|key|num|occurrence_id|sk)$",
        r"^visit_occurrence_id$",
    ]),
    (ROLE_CODE, [
        r"^(icd9|icd10|icd|cpt4?|hcpcs|loinc|snomed|rxnorm|ndc|atc)\w*$",
        r".*_code$", r"^code$", r"^concept_id$", r"^(source|target)_concept_id$",
    ]),
    (ROLE_TIME, [
        r".*(time|date|datetime|timestamp)$", r"^dob$", r".*_at$", r".*_ts$",
        r"^(chart|admit|disch|event|start|end|birth|death)time$",
    ]),
    (ROLE_OUTCOME, [
        r"^(mortality|death|deceased|expired|alive|survival|disposition)$",
        r"^discharge_disposition$", r"^readmit\w*$", r"^outcome$",
        r".*_(flag|status)$",
    ]),
    (ROLE_TEXT, [
        r"^(note|notes|text|narrative|comment|comments|report|description|reason)$",
        r".*_(text|note|narrative|comment|description)$", r"^note_\w+$",
    ]),
]


def infer_role(column_name: str) -> str:
    """Return the structural role for a column name (first matching pattern)."""
    norm = normalize_col(column_name)
    for role, patterns in ROLE_PATTERNS:
        for pat in patterns:
            if re.match(pat, norm):
                return role
    return ROLE_OTHER
