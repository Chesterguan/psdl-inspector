'use client';

import { useState, useCallback, useEffect } from 'react';
import { FileUp, Play, RefreshCw } from 'lucide-react';
import { Editor, ValidationPanel, OutlineTree, CanonicalView, ExportButton, DAGView, BundlePanel, GovernancePanel } from '@/components';
import { api, ValidationResponse, OutlineResponse, CertifiedBundle, VersionInfo } from '@/lib/api';

// Sample scenario for demo (psdl-lang 0.3.1 syntax)
const SAMPLE_SCENARIO = `# PSDL Example: AKI Early Detection
scenario: AKI_Early_Detection
version: "0.3.1"
description: "Detect early signs of Acute Kidney Injury"

signals:
  Cr:
    ref: creatinine
    concept_id: 3016723
    unit: mg/dL

  BUN:
    ref: blood_urea_nitrogen
    concept_id: 3013682
    unit: mg/dL

trends:
  cr_delta_48h:
    expr: delta(Cr, 48h)
    description: "Creatinine change over 48 hours"

  cr_delta_24h:
    expr: delta(Cr, 24h)
    description: "Creatinine change over 24 hours"

  bun_delta_48h:
    expr: delta(BUN, 48h)
    description: "BUN change over 48 hours"

logic:
  aki_stage1:
    when: cr_delta_48h >= 0.3
    severity: medium
    description: "AKI Stage 1 - Creatinine rise >= 0.3 mg/dL in 48h"

  aki_stage2:
    when: cr_delta_48h >= 0.3 AND cr_delta_24h >= 0.5
    severity: high
    description: "AKI Stage 2 - Progressing injury"

  renal_concern:
    when: aki_stage1 AND bun_delta_48h >= 5
    severity: high
    description: "Combined renal function concern"
`;

type TabType = 'validation' | 'outline' | 'dag' | 'bundle' | 'governance' | 'canonical';

export default function Home() {
  const [content, setContent] = useState(SAMPLE_SCENARIO);
  const [activeTab, setActiveTab] = useState<TabType>('validation');

  // Version info
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);

  // API state
  const [validationResult, setValidationResult] = useState<ValidationResponse | null>(null);
  const [outlineResult, setOutlineResult] = useState<OutlineResponse | null>(null);
  const [exportResult, setExportResult] = useState<CertifiedBundle | null>(null);

  // Loading states
  const [isValidating, setIsValidating] = useState(false);
  const [isLoadingOutline, setIsLoadingOutline] = useState(false);
  const [isLoadingExport, setIsLoadingExport] = useState(false);

  // Error state
  const [apiError, setApiError] = useState<string | null>(null);

  // Governance data (user input for IRB preparation)
  const [governanceData, setGovernanceData] = useState({
    clinicalSummary: '',
    justification: '',
    riskAssessment: '',
  });

  const handleValidate = useCallback(async () => {
    if (!content.trim()) return;

    setIsValidating(true);
    setIsLoadingOutline(true);
    setIsLoadingExport(true);
    setApiError(null);

    try {
      // Run validation
      const validation = await api.validate(content);
      setValidationResult(validation);

      // If valid, also fetch outline and export data
      if (validation.valid) {
        const [outline, exportData] = await Promise.all([
          api.getOutline(content),
          api.exportBundle({ content }),
        ]);
        setOutlineResult(outline);
        setExportResult(exportData);
      } else {
        setOutlineResult(null);
        setExportResult(null);
      }
    } catch (error) {
      setApiError(error instanceof Error ? error.message : 'API request failed');
      setValidationResult(null);
      setOutlineResult(null);
      setExportResult(null);
    } finally {
      setIsValidating(false);
      setIsLoadingOutline(false);
      setIsLoadingExport(false);
    }
  }, [content]);

  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result;
      if (typeof text === 'string') {
        setContent(text);
        // Clear previous results
        setValidationResult(null);
        setOutlineResult(null);
        setExportResult(null);
      }
    };
    reader.readAsText(file);
  }, []);

  const handleReset = useCallback(() => {
    setContent(SAMPLE_SCENARIO);
    setValidationResult(null);
    setOutlineResult(null);
    setExportResult(null);
    setApiError(null);
  }, []);

  // Fetch version info and auto-validate on first load
  useEffect(() => {
    api.getVersion().then(setVersionInfo).catch(console.error);
    handleValidate();
  }, []);

  const tabs: { id: TabType; label: string }[] = [
    { id: 'validation', label: 'Validation' },
    { id: 'outline', label: 'Outline' },
    { id: 'dag', label: 'DAG' },
    { id: 'bundle', label: 'Bundle' },
    { id: 'governance', label: 'Governance' },
    { id: 'canonical', label: 'Canonical' },
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">PSDL Inspector</h1>
            <p className="text-sm text-gray-500">
              Validate, analyze, and export PSDL scenarios
            </p>
          </div>
          <div className="flex items-center gap-4">
            {versionInfo && (
              <div className="text-xs text-gray-500 text-right">
                <div>Inspector v{versionInfo.inspector}</div>
                <div>psdl-lang v{versionInfo.psdl_lang}</div>
              </div>
            )}
            <ExportButton
              exportData={exportResult}
              scenarioName={outlineResult?.scenario || 'scenario'}
              isLoading={isLoadingExport}
            />
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left panel: Editor */}
        <div className="w-1/2 flex flex-col border-r border-gray-800">
          {/* Editor toolbar */}
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-gray-900">
            <span className="text-sm text-gray-400">PSDL Scenario</span>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 rounded cursor-pointer transition-colors">
                <FileUp className="w-4 h-4" />
                Upload
                <input
                  type="file"
                  accept=".yaml,.yml"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </label>
              <button
                onClick={handleReset}
                className="flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 rounded transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Reset
              </button>
              <button
                onClick={handleValidate}
                disabled={isValidating}
                className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 rounded transition-colors disabled:opacity-50"
              >
                <Play className="w-4 h-4" />
                {isValidating ? 'Validating...' : 'Validate'}
              </button>
            </div>
          </div>

          {/* Editor */}
          <div className="flex-1 overflow-hidden p-4">
            <Editor
              value={content}
              onChange={setContent}
              className="h-full"
            />
          </div>
        </div>

        {/* Right panel: Results */}
        <div className="w-1/2 flex flex-col">
          {/* Tabs */}
          <div className="flex border-b border-gray-800 bg-gray-900">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-auto">
            {apiError && (
              <div className="m-4 p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
                <strong>API Error:</strong> {apiError}
                <p className="mt-1 text-red-500">
                  Make sure the backend is running on http://localhost:8200
                </p>
              </div>
            )}

            {activeTab === 'validation' && (
              <ValidationPanel
                isValid={validationResult?.valid ?? null}
                errors={validationResult?.errors || []}
                warnings={validationResult?.warnings || []}
                isLoading={isValidating}
              />
            )}

            {activeTab === 'outline' && (
              <OutlineTree outline={outlineResult} isLoading={isLoadingOutline} />
            )}

            {activeTab === 'dag' && (
              <div className="h-full min-h-[500px]">
                <DAGView outline={outlineResult} />
              </div>
            )}

            {activeTab === 'bundle' && (
              <BundlePanel bundle={exportResult} loading={isLoadingExport} />
            )}

            {activeTab === 'governance' && (
              <GovernancePanel
                outline={outlineResult}
                governanceData={governanceData}
                onGovernanceChange={setGovernanceData}
                content={content}
                isLoading={isLoadingOutline}
              />
            )}

            {activeTab === 'canonical' && (
              <CanonicalView exportData={exportResult} isLoading={isLoadingExport} />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
