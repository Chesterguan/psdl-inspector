"""Tests for psdl_meds.schema — MEDS column model + pyarrow schema."""

import pyarrow as pa

from psdl_meds.schema import MEDS_COLUMNS, meds_arrow_schema


def test_meds_columns_minimal_set():
    # MEDS minimum required columns per the spec.
    assert {"subject_id", "time", "code"}.issubset(set(MEDS_COLUMNS))


def test_meds_columns_includes_numeric_value():
    assert "numeric_value" in MEDS_COLUMNS


def test_arrow_schema_subject_id_is_int64():
    schema = meds_arrow_schema()
    assert schema.field("subject_id").type == pa.int64()


def test_arrow_schema_time_is_timestamp_us():
    schema = meds_arrow_schema()
    assert schema.field("time").type == pa.timestamp("us")


def test_arrow_schema_code_is_string():
    schema = meds_arrow_schema()
    assert schema.field("code").type == pa.string()


def test_arrow_schema_numeric_value_is_nullable_float():
    schema = meds_arrow_schema()
    field = schema.field("numeric_value")
    assert field.nullable is True
    assert field.type in (pa.float32(), pa.float64())
