"""Tests for psdl_meds.codes — MEDS code-string formatter."""

import pytest

from psdl_meds.codes import format_code


def test_format_code_basic_loinc():
    assert format_code("LOINC", "2160-0") == "LOINC/2160-0"


def test_format_code_basic_icd10():
    assert format_code("ICD10CM", "E11.9") == "ICD10CM/E11.9"


def test_format_code_strips_whitespace():
    assert format_code("  LOINC  ", "  2160-0  ") == "LOINC/2160-0"


def test_format_code_uppercases_vocab():
    assert format_code("loinc", "2160-0") == "LOINC/2160-0"


def test_format_code_preserves_code_case():
    # Concept codes are case-sensitive in source vocabularies.
    assert format_code("SNOMED", "Abc123") == "SNOMED/Abc123"


def test_format_code_rejects_empty_vocab():
    with pytest.raises(ValueError, match="vocabulary"):
        format_code("", "2160-0")


def test_format_code_rejects_empty_code():
    with pytest.raises(ValueError, match="concept_code"):
        format_code("LOINC", "")


def test_format_code_rejects_slash_in_vocab():
    # Slashes would break the MEDS code-string convention.
    with pytest.raises(ValueError, match="slash"):
        format_code("LO/INC", "2160-0")
