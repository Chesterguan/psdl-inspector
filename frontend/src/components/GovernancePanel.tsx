'use client';

import { useState } from 'react';
import { FileText, Download, AlertCircle } from 'lucide-react';
import type { OutlineResponse } from '@/lib/api';

export interface GovernanceData {
  clinicalSummary: string;
  justification: string;
  riskAssessment: string;
}

interface GovernancePanelProps {
  outline: OutlineResponse | null;
  governanceData: GovernanceData;
  onGovernanceChange: (data: GovernanceData) => void;
  content: string;
  isLoading: boolean;
}

export default function GovernancePanel({
  outline,
  governanceData,
  onGovernanceChange,
  content,
  isLoading,
}: GovernancePanelProps) {
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExportWord = async () => {
    if (!content.trim()) return;

    setIsExporting(true);
    setExportError(null);

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8200';
      const response = await fetch(`${apiBase}/api/export/irb-document`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content,
          governance: {
            clinical_summary: governanceData.clinicalSummary,
            justification: governanceData.justification,
            risk_assessment: governanceData.riskAssessment,
          },
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to generate document');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${outline?.scenario || 'scenario'}_IRB_Documentation.docx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      setExportError(error instanceof Error ? error.message : 'Export failed');
    } finally {
      setIsExporting(false);
    }
  };

  const handleFieldChange = (field: keyof GovernanceData, value: string) => {
    onGovernanceChange({
      ...governanceData,
      [field]: value,
    });
  };

  if (isLoading) {
    return (
      <div className="p-4 text-gray-400 text-sm">
        Loading scenario information...
      </div>
    );
  }

  const signalsCount = outline?.signals?.length || 0;
  const logicCount = outline?.logic?.length || 0;
  const trendsCount = outline?.trends?.length || 0;

  return (
    <div className="h-full overflow-auto p-4 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2 text-lg font-semibold text-gray-100">
        <FileText className="w-5 h-5" />
        Governance - IRB Preparation
      </div>

      {/* Scenario Information (auto-derived) */}
      <section>
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
          Scenario Information
        </h3>
        <div className="bg-gray-800 rounded-lg p-4 space-y-2 border border-gray-700">
          <div className="flex justify-between">
            <span className="text-gray-400">Name:</span>
            <span className="font-semibold text-gray-200">
              {outline?.scenario || 'N/A'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Version:</span>
            <span className="font-mono text-sm text-gray-200">
              {outline?.version || 'N/A'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Data Elements (Signals):</span>
            <span className="font-mono text-sm text-blue-400">
              {signalsCount} signal{signalsCount !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Trends:</span>
            <span className="font-mono text-sm text-purple-400">
              {trendsCount} trend{trendsCount !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Logic Rules:</span>
            <span className="font-mono text-sm text-green-400">
              {logicCount} rule{logicCount !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      </section>

      {/* Documentation (user input) */}
      <section>
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
          Documentation
        </h3>
        <div className="space-y-4">
          {/* Clinical Summary */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Clinical Summary <span className="text-red-400">*</span>
            </label>
            <textarea
              value={governanceData.clinicalSummary}
              onChange={(e) => handleFieldChange('clinicalSummary', e.target.value)}
              placeholder="Describe what this algorithm detects and why it matters clinically. What clinical condition or risk is being monitored?"
              className="w-full h-28 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            />
          </div>

          {/* Justification */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Justification <span className="text-red-400">*</span>
            </label>
            <textarea
              value={governanceData.justification}
              onChange={(e) => handleFieldChange('justification', e.target.value)}
              placeholder="Why is this algorithm needed? What clinical problem does it solve? What is the expected benefit to patient care?"
              className="w-full h-28 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            />
          </div>

          {/* Risk Assessment */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Risk Assessment
            </label>
            <textarea
              value={governanceData.riskAssessment}
              onChange={(e) => handleFieldChange('riskAssessment', e.target.value)}
              placeholder="What are the consequences if the algorithm produces false positives or false negatives? What safeguards are in place?"
              className="w-full h-28 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            />
          </div>
        </div>
      </section>

      {/* Export Error */}
      {exportError && (
        <div className="flex items-center gap-2 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{exportError}</span>
        </div>
      )}

      {/* Export Button */}
      <section>
        <button
          onClick={handleExportWord}
          disabled={isExporting || !outline}
          className={`
            flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium w-full justify-center
            transition-colors duration-200
            ${
              outline && !isExporting
                ? 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer'
                : 'bg-gray-700 text-gray-400 cursor-not-allowed'
            }
          `}
        >
          <Download className="w-4 h-4" />
          {isExporting ? 'Generating Document...' : 'Export Word Document'}
        </button>
        <p className="mt-2 text-xs text-gray-500 text-center">
          Generates an editable .docx file for IRB submission preparation
        </p>
      </section>

      {/* Info Note */}
      <section className="bg-blue-900/20 rounded-lg p-4 border border-blue-800/50">
        <h4 className="text-sm font-semibold text-blue-300 mb-2">About IRB Preparation</h4>
        <p className="text-sm text-blue-200/80">
          This tool helps you prepare documentation for Institutional Review Board (IRB)
          submissions. The exported Word document includes algorithm details auto-derived
          from your PSDL specification, combined with your clinical narrative.
          The document is editable - you can further customize it before submission.
        </p>
      </section>
    </div>
  );
}
