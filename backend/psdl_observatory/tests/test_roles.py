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
    ("patient", ROLE_PATIENT),
    ("person", ROLE_PATIENT),
    # encounter
    ("encounter_id", ROLE_ENCOUNTER),
    ("visit_occurrence_id", ROLE_ENCOUNTER),
    ("hadm_id", ROLE_ENCOUNTER),
    ("stay_id", ROLE_ENCOUNTER),
    ("admission_id", ROLE_ENCOUNTER),
    ("encounter", ROLE_ENCOUNTER),
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
    # _flag/_status must be clinically anchored — these are NOT outcomes
    ("marital_status", ROLE_OTHER),
    ("active_flag", ROLE_OTHER),
    ("employment_status", ROLE_OTHER),
    # clinically-stemmed flag/status ARE outcomes
    ("vital_status", ROLE_OUTCOME),
    ("discharge_status", ROLE_OUTCOME),
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


@pytest.mark.parametrize("col,role", [
    # false positives that must NOT be time (the .*date$/.*time$ bug)
    ("update", ROLE_OTHER),
    ("candidate", ROLE_OTHER),
    ("validate", ROLE_OTHER),
    ("mandate", ROLE_OTHER),
    # documented decision: *_code is code (incl. zip/error) — acceptable noise
    ("zip_code", ROLE_CODE),
    ("error_code", ROLE_CODE),
    # bare birthdate/deathdate concatenated forms
    ("birthdate", ROLE_TIME),
])
def test_infer_role_false_positives_and_edge_cases(col, role):
    assert infer_role(col) == role


def test_normalize_col_handles_allcaps_acronyms():
    assert normalize_col("MRNNumber") == "mrn_number"
    assert normalize_col("CDWPatientKey") == "cdw_patient_key"


def test_normalize_col_preserves_non_ascii():
    # CJK: must return non-empty and preserve the characters
    result_cjk = normalize_col("注射时间")
    assert result_cjk != ""
    assert result_cjk == "注射时间"
    # accents preserved
    assert normalize_col("naïve_café") == "naïve_café"
    assert normalize_col("DÉCÈS") == "décès"


@pytest.mark.parametrize("col,role", [
    # OMOP *_concept_id backbone -> code (the big fix)
    ("condition_concept_id", ROLE_CODE),
    ("gender_concept_id", ROLE_CODE),
    ("measurement_concept_id", ROLE_CODE),
    ("value_as_concept_id", ROLE_CODE),
    ("visit_concept_id", ROLE_CODE),
    ("source_concept_id", ROLE_CODE),
    # encounter/patient FKs still win over code (precedence)
    ("visit_occurrence_id", ROLE_ENCOUNTER),
    ("person_id", ROLE_PATIENT),
    # i2b2 codes (conservative whitelist) + non-code _cd stays other
    ("concept_cd", ROLE_CODE),
    ("modifier_cd", ROLE_CODE),
    ("units_cd", ROLE_OTHER),
    ("sex_cd", ROLE_OTHER),
    # embedded vocab token
    ("lab_loinc", ROLE_CODE),
    # icd_version must NOT be code (was a false positive)
    ("icd_version", ROLE_OTHER),
    ("icd10", ROLE_CODE),
    ("cpt4", ROLE_CODE),
    # Epic vendor tokens
    ("pat_enc_csn_id", ROLE_ENCOUNTER),
    ("note_csn_id", ROLE_ENCOUNTER),
    ("pat_mrn_id", ROLE_PATIENT),
    # time: Epic _DT suffix + MIMIC bare *time + dod
    ("effective_date_dt", ROLE_TIME),
    ("death_date_dt", ROLE_TIME),
    ("intime", ROLE_TIME),
    ("outtime", ROLE_TIME),
    ("storetime", ROLE_TIME),
    ("edregtime", ROLE_TIME),
    ("dod", ROLE_TIME),
    # note_* no longer all text
    ("note_id", ROLE_OTHER),
    ("note_type", ROLE_OTHER),
    ("note_text", ROLE_TEXT),
    ("clinical_note", ROLE_TEXT),
    # outcome: clinical flags yes, demographic/technical no (anti-phantom-outcome)
    ("hospital_expire_flag", ROLE_OUTCOME),
    ("vital_status", ROLE_OUTCOME),
    ("death_flag", ROLE_OUTCOME),
    ("marital_status", ROLE_OTHER),
    ("active_flag", ROLE_OTHER),
    ("employment_status", ROLE_OTHER),
    # i2b2 blob -> text
    ("observation_blob", ROLE_TEXT),
    # measurement value stays other
    ("value_as_number", ROLE_OTHER),
    ("valuenum", ROLE_OTHER),
])
def test_infer_role_new_cases(col, role):
    assert infer_role(col) == role
