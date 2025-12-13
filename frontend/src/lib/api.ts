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

export interface ExportResponse {
  metadata: Record<string, unknown>;
  scenario: Record<string, unknown>;
  audit: AuditInfo;
  summary: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
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

  async exportBundle(content: string, format: string = 'json'): Promise<ExportResponse> {
    const response = await fetch(`${this.baseUrl}/api/export/bundle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, format }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }
}

export const api = new ApiClient();
