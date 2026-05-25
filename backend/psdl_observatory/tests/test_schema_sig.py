"""Tests for schema signature -- the stable, order-independent file identity."""

from psdl_observatory.schema_sig import normalize_columns, schema_signature


def test_normalize_columns_lowercases_and_strips():
    assert normalize_columns(["  Patient_ID ", "VALUE"]) == ["patient_id", "value"]


def test_signature_is_order_independent():
    # column order must not change the signature (same schema, reordered)
    sig_a = schema_signature(["patient_id", "value"], ["int64", "double"])
    sig_b = schema_signature(["value", "patient_id"], ["double", "int64"])
    assert sig_a == sig_b


def test_signature_changes_with_columns():
    sig_a = schema_signature(["patient_id", "value"], ["int64", "double"])
    sig_c = schema_signature(["patient_id"], ["int64"])
    assert sig_a != sig_c


def test_signature_changes_with_types():
    sig_a = schema_signature(["value"], ["double"])
    sig_b = schema_signature(["value"], ["string"])
    assert sig_a != sig_b


def test_signature_is_hex_digest():
    sig = schema_signature(["a"], ["int64"])
    assert isinstance(sig, str)
    assert len(sig) == 16  # truncated sha256 hex
    int(sig, 16)  # parses as hex
