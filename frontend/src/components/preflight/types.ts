export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type Confidence = 'LOW' | 'MEDIUM' | 'HIGH';
export type RuntimeCategory =
  | 'FAST'
  | 'MODERATE'
  | 'HEAVY'
  | 'EXTREME'
  | 'UNKNOWN';

export interface StudySummary {
  execution_target: string;
  tables: string[];
  domains: string[];
  query_shape: string;
}

export interface LineageNode {
  table: string;
  category: string;
  volume: string;
  est_rows: number | null;
}

export interface LineageEdge {
  source: string;
  target: string;
  kind: string;
  cardinality_transition: string;
}

export interface Lineage {
  nodes: LineageNode[];
  edges: LineageEdge[];
  filters: string[];
}

export interface StageEstimate {
  name: string;
  est_rows: number;
}

export interface ScaleEstimate {
  patients: number | null;
  encounters: number | null;
  events: number | null;
  intermediate_records: number | null;
  output_records: number | null;
  per_stage: StageEstimate[];
  confidence: Confidence;
}

export interface Bottleneck {
  component: string;
  reason: string;
  contribution_pct: number;
}

export interface Optimization {
  action: string;
  rationale: string;
  expected_benefit: string;
}

export interface PreflightReport {
  summary: StudySummary;
  lineage: Lineage;
  scale: ScaleEstimate;
  risk_level: RiskLevel;
  risk_reasons: string[];
  bottlenecks: Bottleneck[];
  optimizations: Optimization[];
  query_plan: unknown | null;
  runtime_category: RuntimeCategory;
  confidence: Confidence;
  notes: string[];
}

export interface CatalogsResponse {
  bundled: string[];
  default: string;
  observatory_available: boolean;
  preflight_available: boolean;
  live_db_available: boolean;
}
