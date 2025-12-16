/**
 * API client for PSDL Inspector backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8200';

export interface ValidationError {
  line: number | null;
  column: number | null;
  message: string;
  severity: string;
  path: string | null;
}

export interface ValidationResponse {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
  parsed: Record<string, unknown> | null;
}

export interface SignalOutline {
  name: string;
  source: string | null;
  concept_id: number | null;
  unit: string | null;
  domain: string | null;
  description: string | null;
  used_by: string[];
}

export interface TrendOutline {
  name: string;
  expr: string;
  description: string | null;
  depends_on: string[];
  used_by: string[];
}

export interface LogicOutline {
  name: string;
  expr: string;
  severity: string | null;
  description: string | null;
  recommendation: string | null;
  depends_on: string[];
  operators: string[];
}

export interface OutlineResponse {
  scenario: string;
  version: string | null;
  description: string | null;
  signals: SignalOutline[];
  trends: TrendOutline[];
  logic: LogicOutline[];
}

export interface AuditInfo {
  intent: string | null;
  rationale: string | null;
  provenance: string | null;
}

export interface ValidationResult {
  psdl_lang_version: string;
  inspector_version: string;
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
}

export interface ScenarioContent {
  name: string;
  version: string | null;
  raw_yaml: string;
  parsed: Record<string, unknown>;
}

export interface CertifiedBundle {
  bundle_version: string;
  certified_at: string;
  checksum: string;
  scenario: ScenarioContent;
  validation: ValidationResult;
  audit: AuditInfo;
  summary: string;
}

// Alias for backward compatibility
export type ExportResponse = CertifiedBundle;

export interface ExportRequest {
  content: string;
  format?: string;
  intent?: string;
  rationale?: string;
  provenance?: string;
}

export interface VersionInfo {
  inspector: string;
  psdl_lang: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  async getVersion(): Promise<VersionInfo> {
    const response = await fetch(`${this.baseUrl}/api/version`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
  }

  async validate(content: string): Promise<ValidationResponse> {
    const response = await fetch(`${this.baseUrl}/api/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async getOutline(content: string): Promise<OutlineResponse> {
    const response = await fetch(`${this.baseUrl}/api/outline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async exportBundle(request: ExportRequest): Promise<CertifiedBundle> {
    const response = await fetch(`${this.baseUrl}/api/export/bundle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async downloadBundle(request: ExportRequest): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/api/export/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.blob();
  }
}

export const api = new ApiClient();
