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
    'note__text' -> 'note_text'; 'MRNNumber' -> 'mrn_number';
    '注射时间' -> '注射时间' (non-ASCII preserved); 'naïve_café' -> 'naïve_café'.
    """
    # split ALL-CAPS run followed by a capitalized word: ACRONYMWord -> ACRONYM_Word
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", name.strip())
    # split camelCase / PascalCase boundaries: aB -> a_B
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", s)
    s = s.lower()
    # non-word (Unicode-aware) runs -> underscore; underscores are \w so are preserved here
    s = re.sub(r"[^\w]+", "_", s, flags=re.UNICODE)
    # collapse repeated underscores, strip ends
    s = re.sub(r"_+", "_", s).strip("_")
    # never return empty (e.g. a pure-symbol/emoji name): fall back to the stripped raw
    return s or name.strip().lower()


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
        r"^patient$", r"^person$",          # bare FK names (e.g. Synthea)
        r".*_mrn_id$", r".*_mrn$",           # Epic PAT_MRN_ID etc.
    ]),
    (ROLE_ENCOUNTER, [
        r"^(encounter|visit|admission|hospitalization|hadm|stay|episode|enc)_?"
        r"(id|key|num|occurrence_id|sk)$",
        r"^encounter$",                      # bare FK name
        r".*_csn_id$", r".*_csn$",           # Epic Contact Serial Number = encounter id
    ]),
    (ROLE_CODE, [
        # exact vocabulary names (no trailing \w* — avoids grabbing icd_version/icd_type)
        r"^(icd9cm|icd10cm|icd9|icd10|icd|cpt4|cpt|hcpcs|loinc|snomed|rxnorm|ndc|atc)$",
        # embedded vocabulary token as a suffix (lab_loinc, dx_icd10, ...)
        r".*_(loinc|icd9|icd10|icd|cpt4|cpt|hcpcs|snomed|rxnorm|ndc)$",
        r".*_code$", r"^code$",
        r".*_concept_id$", r"^concept_id$",  # OMOP coded backbone (condition_concept_id, ...)
        r"^(concept|modifier)_cd$",          # i2b2 fact-table code columns (NOT a blanket *_cd)
    ]),
    (ROLE_TIME, [
        r"^(time|date|datetime|timestamp)$",
        r".*_(time|date|datetime|timestamp|dt|dttm)$",   # +Epic _DT/_DTTM suffix
        r"^dob$", r"^dod$",                              # date of birth / death
        r".*_at$", r".*_ts$",
        # bare concatenated *time forms (incl. MIMIC in/out/store/edreg/edout)
        r"^(chart|admit|disch|event|start|end|birth|death|store|in|out|edreg|edout|reg)time$",
        r"^(birth|death|chart|admit|disch)date$",
    ]),
    (ROLE_OUTCOME, [
        r"^(mortality|death|deceased|expired|alive|survival|disposition)$",
        r"^discharge_disposition$", r"^readmit\w*$", r"^outcome$",
        # clinically-stemmed flag/status/ind ONLY (marital_status/active_flag stay 'other')
        r".*(death|deceased|mortality|expire|expired|survival|vital|discharge|readmission|readmit|alive)_(flag|status|ind)$",
    ]),
    (ROLE_TEXT, [
        r"^(note|notes|text|narrative|comment|comments|report|description|reason)$",
        r".*_(text|note|narrative|comment|description)$",
        r".*_blob$",                         # i2b2 observation_blob etc.
        # NOTE: removed the old r"^note_\w+$" — it stole note_id/note_type/note_*_concept_id
    ]),
]

# Precompiled patterns for performance (infer_role is called over thousands of
# columns in the O2 catalog scan).
_COMPILED_PATTERNS = [(role, [re.compile(p) for p in pats]) for role, pats in ROLE_PATTERNS]


def infer_role(column_name: str) -> str:
    """Return the structural role for a column name (first matching pattern)."""
    norm = normalize_col(column_name)
    for role, compiled in _COMPILED_PATTERNS:
        for rx in compiled:
            if rx.match(norm):
                return role
    return ROLE_OTHER
