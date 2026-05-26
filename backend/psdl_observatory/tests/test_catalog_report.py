"""Tests for the semantic catalog HTML view."""

from psdl_observatory.catalog import CatalogResult, ColumnInfo, SchemaProfile
from psdl_observatory.report import render_catalog_html
from psdl_observatory.roles import ROLE_PATIENT, ROLE_TEXT


def _catalog():
    columns = [
        ColumnInfo("patient_id", ROLE_PATIENT, 3, 2, "EHR/labs/part-0.parquet"),
        ColumnInfo("note_text", ROLE_TEXT, 1, 1, "NOTES/notes-0.parquet"),
    ]
    schemas = [
        SchemaProfile("sigA", 2, ["patient_id", "value"],
                      {"patient": 1, "other": 1}, ["patient"],
                      "patient_dimension", "EHR/labs/part-0.parquet"),
    ]
    return CatalogResult(columns=columns, schemas=schemas)


def test_catalog_html_is_html():
    html = render_catalog_html(_catalog())
    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert "</html>" in html


def test_catalog_html_includes_roles_and_columns():
    html = render_catalog_html(_catalog())
    assert "patient_id" in html
    assert "patient" in html
    assert "note_text" in html
    assert "patient_dimension" in html


def test_catalog_html_escapes():
    cols = [ColumnInfo("weird<script>", "other", 1, 1, "x/<b>.parquet")]
    html = render_catalog_html(CatalogResult(columns=cols, schemas=[]))
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<b>.parquet" not in html
    assert "&lt;b&gt;.parquet" in html
