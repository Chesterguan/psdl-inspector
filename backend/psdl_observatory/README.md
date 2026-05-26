# psdl-observatory

EDW Observatory (O1): metadata-only inventory scanner for healthcare parquet
lakes. Reads parquet footers only — never row data, never PHI — and emits a
filesystem inventory, duplicate-filename report, scan summary, and static HTML.

File identity is `relative_path + schema_signature`, not filename (filenames
like `deid_notes_cleaned_0.parquet` recur across datasets and are not globally
meaningful).

Inspector ships the full scanner + CLI + HTML report. PSDL Workbench consumes
these core APIs and adds institutional/enhanced functions.
