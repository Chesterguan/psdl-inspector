'use client';

import type { CertifiedBundle } from '@/lib/api';

interface CanonicalViewProps {
  exportData: CertifiedBundle | null;
  isLoading: boolean;
}

export default function CanonicalView({ exportData, isLoading }: CanonicalViewProps) {
  if (isLoading) {
    return (
      <div className="p-4 text-muted text-sm">
        Generating canonical view...
      </div>
    );
  }

  if (!exportData) {
    return (
      <div className="p-4 text-muted text-sm">
        No data available. Validate a scenario first.
      </div>
    );
  }

  return (
    <div className="p-4 font-mono text-sm">
      {/* Metadata header */}
      <div className="mb-4 pb-3 border-b border-border text-xs text-muted">
        <div>Certified: {new Date(exportData.certified_at).toLocaleString()}</div>
        <div>Checksum: {exportData.checksum}</div>
        <div>psdl-lang: {exportData.validation.psdl_lang_version}</div>
      </div>

      {/* Summary */}
      <pre className="whitespace-pre-wrap text-foreground bg-surface p-4 rounded-lg overflow-auto border border-border">
        {exportData.summary}
      </pre>
    </div>
  );
}
