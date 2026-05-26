"""Build a semantic catalog from a scan: per-column roles + per-schema profiles.

Pure, metadata-only — operates on the O1 ScanResult (footer-derived column
names), never reads row data.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from psdl_observatory.models import ScanResult
from psdl_observatory.roles import (
    ALL_ROLES,
    ROLE_CODE,
    ROLE_ENCOUNTER,
    ROLE_OTHER,
    ROLE_PATIENT,
    ROLE_TEXT,
    ROLE_TIME,
    infer_role,
    normalize_col,
)


@dataclass
class ColumnInfo:
    """A distinct (normalized) column name across the lake + its inferred role."""

    normalized: str
    role: str
    file_count: int          # number of files this column appears in
    schema_count: int        # number of distinct schema signatures it appears in
    example_path: str        # one relative path where it occurs


@dataclass
class SchemaProfile:
    """Semantic profile of one distinct schema signature."""

    schema_signature: str
    num_files: int
    columns: List[str]                       # normalized column names
    role_counts: Dict[str, int]              # role -> count of columns
    roles_present: List[str]                 # roles with count > 0 (stable order)
    table_kind: str                          # heuristic label, e.g. 'clinical_notes'
    example_path: str

    @property
    def num_columns(self) -> int:
        return len(self.columns)


@dataclass
class CatalogResult:
    columns: List[ColumnInfo] = field(default_factory=list)
    schemas: List[SchemaProfile] = field(default_factory=list)


def _classify_table_kind(roles_present: List[str]) -> str:
    """A light, documented heuristic label for a schema based on its roles."""
    rp = set(roles_present)
    if ROLE_TEXT in rp:
        return "clinical_notes"
    if ROLE_PATIENT in rp and ROLE_ENCOUNTER in rp and ROLE_TIME in rp:
        return "encounter_events"
    if ROLE_CODE in rp and (ROLE_PATIENT in rp or ROLE_ENCOUNTER in rp):
        return "coded_clinical_events"
    if ROLE_PATIENT in rp and ROLE_ENCOUNTER not in rp:
        return "patient_dimension"
    if ROLE_ENCOUNTER in rp:
        return "encounter_dimension"
    return "reference_or_other"


def build_catalog(scan: ScanResult) -> CatalogResult:
    # --- per-column aggregation ---
    col_files: Dict[str, int] = Counter()
    col_schemas: Dict[str, set] = defaultdict(set)
    col_example: Dict[str, str] = {}
    for f in scan.files:
        seen_in_file = set()
        for raw in f.columns:
            norm = normalize_col(raw)
            if norm in seen_in_file:
                continue          # count a column once per file
            seen_in_file.add(norm)
            col_files[norm] += 1
            col_schemas[norm].add(f.schema_signature)
            col_example.setdefault(norm, f.relative_path)

    columns = [
        ColumnInfo(
            normalized=norm,
            role=infer_role(norm),
            file_count=col_files[norm],
            schema_count=len(col_schemas[norm]),
            example_path=col_example[norm],
        )
        for norm in sorted(col_files)
    ]

    # --- per-schema profiles (one representative file per signature) ---
    sig_files: Dict[str, int] = Counter()
    sig_repr = {}  # signature -> representative ParquetFileInfo
    for f in scan.files:
        sig_files[f.schema_signature] += 1
        sig_repr.setdefault(f.schema_signature, f)

    schemas = []
    for sig in sorted(sig_repr):
        f = sig_repr[sig]
        norm_cols = [normalize_col(c) for c in f.columns]
        counts = {r: 0 for r in ALL_ROLES}
        for nc in norm_cols:
            counts[infer_role(nc)] += 1
        roles_present = [r for r in ALL_ROLES if r != ROLE_OTHER and counts[r] > 0]
        schemas.append(SchemaProfile(
            schema_signature=sig,
            num_files=sig_files[sig],
            columns=norm_cols,
            role_counts=counts,
            roles_present=roles_present,
            table_kind=_classify_table_kind(roles_present),
            example_path=f.relative_path,
        ))

    return CatalogResult(columns=columns, schemas=schemas)
