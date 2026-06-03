export interface Provenance {
  scanned_at: string | null;
  root: string | null;
  file_count: number | null;
  schema_count: number | null;
  scan_error_count: number | null;
  scanner_version: string | null;
}

export interface CatalogStatus {
  configured: boolean;
  available: boolean;
  provenance?: Provenance | null;
  stale?: boolean;
  stale_threshold_days?: number;
  reason?: string | null;
}

export interface SchemaProfile {
  schema_signature: string;
  table_kind: string;
  num_files: number;
  num_rows: number;
  roles_present: string[];
  role_counts: Record<string, number>;
  columns: string[];
  example_path: string;
}

export interface ColumnInfo {
  normalized: string;
  role: string;
  file_count: number;
  schema_count: number;
  example_path: string;
}

export interface Catalog {
  catalog_version?: string;
  provenance?: Provenance;
  schemas?: SchemaProfile[];
  columns?: ColumnInfo[];
  available?: boolean;
  reason?: string | null;
}
