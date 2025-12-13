'use client';

import type { ExportResponse } from '@/lib/api';

interface CanonicalViewProps {
  exportData: ExportResponse | null;
  isLoading: boolean;
}

export default function CanonicalView({ exportData, isLoading }: CanonicalViewProps) {
  if (isLoading) {
    return (
      <div className="p-4 text-gray-400 text-sm">
        Generating canonical view...
      </div>
    );
  }

  if (!exportData) {
    return (
      <div className="p-4 text-gray-500 text-sm">
        No data available. Validate a scenario first.
      </div>
    );
  }

  return (
    <div className="p-4 font-mono text-sm">
      {/* Metadata header */}
      <div className="mb-4 pb-3 border-b border-gray-700 text-xs text-gray-500">
        <div>Exported: {exportData.metadata.exported_at as string}</div>
        <div>Checksum: {exportData.metadata.checksum as string}</div>
      </div>

      {/* Summary */}
      <pre className="whitespace-pre-wrap text-gray-300 bg-gray-900 p-4 rounded-lg overflow-auto">
        {exportData.summary}
      </pre>
    </div>
  );
}
