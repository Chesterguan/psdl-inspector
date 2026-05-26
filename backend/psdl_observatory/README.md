# psdl-observatory

EDW Observatory (O1): metadata-only inventory scanner for healthcare parquet
lakes. Reads parquet footers only — never row data, never PHI — and emits a
filesystem inventory, duplicate-filename report, scan summary, and static HTML.

File identity is `relative_path + schema_signature`, not filename (filenames
like `deid_notes_cleaned_0.parquet` recur across datasets and are not globally
meaningful).

Inspector ships the full scanner + CLI + HTML report. PSDL Workbench consumes
these core APIs and adds institutional/enhanced functions.

## Semantic Schema Registry (O2)

Beyond the raw inventory, `build_catalog()` infers structural column roles
(patient / encounter / time / text / code / outcome) from column names — purely
heuristic, never clinical concept mapping — and emits `column_catalog.csv` +
`schema_semantic_catalog.csv` plus a catalog HTML view. CLI: `psdl-observatory
catalog <root> --out <dir> [--html]`.
