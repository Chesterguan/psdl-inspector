"""Tests for column-name normalization + structural role inference."""

import pytest

from psdl_observatory.roles import (
    ROLE_OTHER,
    ROLE_PATIENT,
    ROLE_ENCOUNTER,
    ROLE_TIME,
    ROLE_TEXT,
    ROLE_CODE,
    ROLE_OUTCOME,
    infer_role,
    normalize_col,
)


def test_normalize_col_lowercases_and_unifies_separators():
    assert normalize_col("  Patient ID ") == "patient_id"
    assert normalize_col("encounterID") == "encounter_id"
    assert normalize_col("Visit-Occurrence-ID") == "visit_occurrence_id"
    assert normalize_col("charttime") == "charttime"
    assert normalize_col("note__text") == "note_text"


@pytest.mark.parametrize("col,role", [
    # patient
    ("patient_id", ROLE_PATIENT),
    ("person_id", ROLE_PATIENT),
    ("subject_id", ROLE_PATIENT),
    ("mrn", ROLE_PATIENT),
    ("person_key", ROLE_PATIENT),
    # encounter
    ("encounter_id", ROLE_ENCOUNTER),
    ("visit_occurrence_id", ROLE_ENCOUNTER),
    ("hadm_id", ROLE_ENCOUNTER),
    ("stay_id", ROLE_ENCOUNTER),
    ("admission_id", ROLE_ENCOUNTER),
    # code (checked before time so *_code wins over nothing)
    ("diagnosis_code", ROLE_CODE),
    ("icd10_code", ROLE_CODE),
    ("loinc", ROLE_CODE),
    ("cpt4", ROLE_CODE),
    ("concept_id", ROLE_CODE),
    ("ndc", ROLE_CODE),
    # time
    ("charttime", ROLE_TIME),
    ("admittime", ROLE_TIME),
    ("event_time", ROLE_TIME),
    ("birth_date", ROLE_TIME),
    ("dob", ROLE_TIME),
    ("created_at", ROLE_TIME),
    ("measurement_datetime", ROLE_TIME),
    # outcome
    ("mortality", ROLE_OUTCOME),
    ("deceased", ROLE_OUTCOME),
    ("discharge_disposition", ROLE_OUTCOME),
    ("expired", ROLE_OUTCOME),
    ("readmitted", ROLE_OUTCOME),
    # text
    ("note_text", ROLE_TEXT),
    ("clinical_note", ROLE_TEXT),
    ("narrative", ROLE_TEXT),
    ("report_text", ROLE_TEXT),
    # other
    ("value", ROLE_OTHER),
    ("row_id", ROLE_OTHER),
    ("quantity", ROLE_OTHER),
])
def test_infer_role(col, role):
    assert infer_role(col) == role


def test_infer_role_precedence_id_beats_code():
    # patient_id ends in _id, must be patient (not code despite containing 'id')
    assert infer_role("patient_id") == ROLE_PATIENT


def test_infer_role_precedence_date_beats_outcome():
    # a death DATE is a timestamp → time wins over the outcome 'death' token
    assert infer_role("death_date") == ROLE_TIME
    # but a bare mortality flag is outcome
    assert infer_role("death_flag") == ROLE_OUTCOME


def test_infer_role_is_case_insensitive():
    assert infer_role("Patient_ID") == ROLE_PATIENT
    assert infer_role("ChartTime") == ROLE_TIME
