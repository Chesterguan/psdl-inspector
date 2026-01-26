'use client';

import { Download } from 'lucide-react';
import type { CertifiedBundle } from '@/lib/api';

interface ExportButtonProps {
  exportData: CertifiedBundle | null;
  scenarioName: string;
  isLoading: boolean;
}

export default function ExportButton({ exportData, scenarioName, isLoading }: ExportButtonProps) {
  const handleExport = () => {
    if (!exportData) return;

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${scenarioName || 'scenario'}_audit_bundle.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <button
      onClick={handleExport}
      disabled={!exportData || isLoading}
      className={`
        flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-xl font-medium text-sm
        transition-all duration-200
        ${
          exportData && !isLoading
            ? 'bg-accent hover:bg-accent-hover text-white cursor-pointer shadow-sm hover:shadow-md'
            : 'bg-surface-hover text-muted cursor-not-allowed border border-border'
        }
      `}
    >
      <Download className="w-4 h-4" />
      Export Audit Bundle
    </button>
  );
}
