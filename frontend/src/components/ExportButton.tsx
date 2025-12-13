'use client';

import { Download } from 'lucide-react';
import type { ExportResponse } from '@/lib/api';

interface ExportButtonProps {
  exportData: ExportResponse | null;
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
        flex items-center gap-2 px-4 py-2 rounded-lg font-medium
        transition-colors duration-200
        ${
          exportData && !isLoading
            ? 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer'
            : 'bg-gray-700 text-gray-400 cursor-not-allowed'
        }
      `}
    >
      <Download className="w-4 h-4" />
      Export Audit Bundle
    </button>
  );
}
