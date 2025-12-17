'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  FileUp, Play, RefreshCw, ChevronRight, ChevronLeft,
  Check, AlertCircle, Loader2, Edit3, Sparkles,
  Download, Eye, FileText, Shield, Maximize2, X
} from 'lucide-react';
import { Editor, DAGView, GovernancePanel, ExportButton, GenerationPanel, ThemeToggle, Logo } from '@/components';
import { api, ValidationResponse, OutlineResponse, CertifiedBundle, VersionInfo } from '@/lib/api';

// Sample scenario for demo
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

type WizardStep = 'input' | 'preview' | 'export';
type InputMode = 'manual' | 'llm';

interface StepInfo {
  id: WizardStep;
  label: string;
  icon: React.ReactNode;
}

const STEPS: StepInfo[] = [
  { id: 'input', label: 'Input', icon: <Edit3 className="w-4 h-4" /> },
  { id: 'preview', label: 'Preview', icon: <Eye className="w-4 h-4" /> },
  { id: 'export', label: 'Export', icon: <Download className="w-4 h-4" /> },
];

export default function Home() {
  // Wizard state
  const [currentStep, setCurrentStep] = useState<WizardStep>('input');
  const [inputMode, setInputMode] = useState<InputMode>('manual');

  // Scenario state
  const [content, setContent] = useState(SAMPLE_SCENARIO);
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);

  // API results
  const [validationResult, setValidationResult] = useState<ValidationResponse | null>(null);
  const [outlineResult, setOutlineResult] = useState<OutlineResponse | null>(null);
  const [exportResult, setExportResult] = useState<CertifiedBundle | null>(null);

  // Loading states
  const [isValidating, setIsValidating] = useState(false);
  const [isLoadingOutline, setIsLoadingOutline] = useState(false);
  const [isLoadingExport, setIsLoadingExport] = useState(false);

  // Error state
  const [apiError, setApiError] = useState<string | null>(null);

  // UI state
  const [showFullEditor, setShowFullEditor] = useState(false);

  // Governance data
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
      const validation = await api.validate(content);
      setValidationResult(validation);

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

  // Handle generated YAML from LLM - already validated during generation
  const handleUseGenerated = useCallback(async (result: { yaml: string; valid: boolean; errors: string[]; warnings: string[] }) => {
    setContent(result.yaml);
    setInputMode('manual');

    // Set validation result from generation (avoid re-validation)
    const validationResponse: ValidationResponse = {
      valid: result.valid,
      errors: result.errors.map((msg) => ({
        message: msg,
        line: null,
        column: null,
        severity: 'error',
        path: null,
      })),
      warnings: result.warnings.map((msg) => ({
        message: msg,
        line: null,
        column: null,
        severity: 'warning',
        path: null,
      })),
      parsed: null,
    };
    setValidationResult(validationResponse);

    // If valid, fetch outline and export data
    if (result.valid) {
      setIsLoadingOutline(true);
      setIsLoadingExport(true);
      try {
        const [outline, exportData] = await Promise.all([
          api.getOutline(result.yaml),
          api.exportBundle({ content: result.yaml }),
        ]);
        setOutlineResult(outline);
        setExportResult(exportData);
      } catch (error) {
        setApiError(error instanceof Error ? error.message : 'Failed to load outline/export');
      } finally {
        setIsLoadingOutline(false);
        setIsLoadingExport(false);
      }
    } else {
      setOutlineResult(null);
      setExportResult(null);
    }
  }, []);

  // Fetch version info on mount
  useEffect(() => {
    api.getVersion().then(setVersionInfo).catch(console.error);
  }, []);

  // Validation status helpers
  const isValid = validationResult?.valid === true;
  const hasErrors = validationResult && !validationResult.valid;
  const errorCount = validationResult?.errors?.length || 0;
  const warningCount = validationResult?.warnings?.length || 0;

  // Navigation helpers
  const canProceed = isValid && outlineResult;

  const goToStep = (step: WizardStep) => {
    if (step !== 'input' && !isValid) return;
    setCurrentStep(step);
  };

  const goNext = () => {
    const stepOrder: WizardStep[] = ['input', 'preview', 'export'];
    const currentIndex = stepOrder.indexOf(currentStep);
    if (currentIndex < stepOrder.length - 1) {
      goToStep(stepOrder[currentIndex + 1]);
    }
  };

  const goBack = () => {
    const stepOrder: WizardStep[] = ['input', 'preview', 'export'];
    const currentIndex = stepOrder.indexOf(currentStep);
    if (currentIndex > 0) {
      setCurrentStep(stepOrder[currentIndex - 1]);
    }
  };

  // Step status for indicators
  const getStepStatus = (step: WizardStep): 'complete' | 'current' | 'upcoming' | 'error' => {
    const stepOrder: WizardStep[] = ['input', 'preview', 'export'];
    const currentIndex = stepOrder.indexOf(currentStep);
    const stepIndex = stepOrder.indexOf(step);

    if (step === 'input' && hasErrors) return 'error';
    if (stepIndex < currentIndex) return 'complete';
    if (stepIndex === currentIndex) return 'current';
    return 'upcoming';
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col transition-colors">
      {/* Header */}
      <header className="border-b border-border bg-surface px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Logo size={32} />
            <div>
              <h1 className="text-lg font-bold">PSDL Inspector</h1>
              <p className="text-xs text-muted">
                Validate, analyze, and export PSDL scenarios
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {versionInfo && (
              <div className="text-xs text-muted text-right hidden sm:block">
                <div>psdl-lang v{versionInfo.psdl_lang}</div>
              </div>
            )}
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Step Indicator with Navigation */}
      <div className="sticky top-0 z-10 border-b border-border bg-surface/95 backdrop-blur px-6 py-3">
        <div className="flex items-center justify-between max-w-5xl mx-auto">
          {/* Back Button */}
          <button
            onClick={goBack}
            disabled={currentStep === 'input'}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition-colors ${
              currentStep === 'input'
                ? 'text-muted cursor-not-allowed opacity-50'
                : 'bg-surface-hover hover:bg-border'
            }`}
          >
            <ChevronLeft className="w-4 h-4" />
            Back
          </button>

          {/* Steps */}
          <div className="flex items-center gap-1">
            {STEPS.map((step, index) => {
              const status = getStepStatus(step.id);
              const isClickable = status === 'complete' || status === 'current' || (step.id === 'input');

              return (
                <div key={step.id} className="flex items-center">
                  {index > 0 && (
                    <div className={`w-8 h-0.5 transition-colors ${
                      status === 'complete' || (index <= STEPS.findIndex(s => s.id === currentStep))
                        ? 'bg-accent'
                        : 'bg-border'
                    }`} />
                  )}
                  <button
                    onClick={() => isClickable && goToStep(step.id)}
                    disabled={!isClickable}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-all ${
                      status === 'current'
                        ? 'bg-accent text-white'
                        : status === 'complete'
                        ? 'bg-green-600/20 text-green-600 dark:text-green-400 hover:bg-green-600/30'
                        : status === 'error'
                        ? 'bg-red-600/20 text-red-600 dark:text-red-400'
                        : 'text-muted cursor-not-allowed'
                    }`}
                  >
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${
                      status === 'current' ? 'bg-blue-500 text-white' :
                      status === 'complete' ? 'bg-green-600 text-white' :
                      status === 'error' ? 'bg-red-600 text-white' :
                      'bg-border'
                    }`}>
                      {status === 'complete' ? <Check className="w-3 h-3" /> :
                       status === 'error' ? <AlertCircle className="w-3 h-3" /> :
                       index + 1}
                    </div>
                    <span className="hidden sm:inline">{step.label}</span>
                  </button>
                </div>
              );
            })}
          </div>

          {/* Next Button */}
          {currentStep === 'export' ? (
            <div className="w-20" />
          ) : (
            <button
              onClick={goNext}
              disabled={!canProceed || isValidating}
              className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                canProceed && !isValidating
                  ? 'bg-accent hover:bg-blue-700 text-white'
                  : 'bg-surface-hover text-muted cursor-not-allowed opacity-50'
              }`}
            >
              {isValidating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="hidden sm:inline">Validating</span>
                </>
              ) : (
                <>
                  Next
                  <ChevronRight className="w-4 h-4" />
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {apiError && (
          <div className="m-4 p-4 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg text-red-700 dark:text-red-400 text-sm">
            <strong>API Error:</strong> {apiError}
            <p className="mt-1 text-red-600 dark:text-red-500">
              Make sure the backend is running on http://localhost:8200
            </p>
          </div>
        )}

        {/* Step 1: Input */}
        {currentStep === 'input' && (
          <div className="h-full flex flex-col">
            {/* Mode Toggle */}
            <div className="flex items-center justify-center gap-4 p-3 border-b border-border bg-surface/30">
              <button
                onClick={() => setInputMode('manual')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                  inputMode === 'manual'
                    ? 'bg-accent text-white shadow-lg'
                    : 'bg-surface-hover text-muted hover:bg-border'
                }`}
              >
                <Edit3 className="w-4 h-4" />
                Manual Editor
              </button>
              <span className="text-muted text-sm">or</span>
              <button
                onClick={() => setInputMode('llm')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                  inputMode === 'llm'
                    ? 'bg-purple-600 text-white shadow-lg'
                    : 'bg-surface-hover text-muted hover:bg-border'
                }`}
              >
                <Sparkles className="w-4 h-4" />
                AI Generate
              </button>
            </div>

            {/* Manual Mode: Editor */}
            {inputMode === 'manual' && (
              <div className="flex-1 flex flex-col min-h-0">
                {/* Editor Toolbar */}
                <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted">PSDL Scenario</span>
                    {content.split('\n').length > 50 && (
                      <span className="text-xs text-muted bg-surface-hover px-2 py-0.5 rounded">
                        {content.split('\n').length} lines
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setShowFullEditor(true)}
                      className="flex items-center gap-1 px-2 py-1 text-sm bg-surface-hover hover:bg-border rounded transition-colors"
                      title="Expand editor"
                    >
                      <Maximize2 className="w-4 h-4" />
                    </button>
                    <label className="flex items-center gap-1 px-2 py-1 text-sm bg-surface-hover hover:bg-border rounded cursor-pointer transition-colors">
                      <FileUp className="w-4 h-4" />
                      <span className="hidden sm:inline">Upload</span>
                      <input
                        type="file"
                        accept=".yaml,.yml"
                        onChange={handleFileUpload}
                        className="hidden"
                      />
                    </label>
                    <button
                      onClick={handleReset}
                      className="flex items-center gap-1 px-2 py-1 text-sm bg-surface-hover hover:bg-border rounded transition-colors"
                    >
                      <RefreshCw className="w-4 h-4" />
                      <span className="hidden sm:inline">Reset</span>
                    </button>
                    <button
                      onClick={handleValidate}
                      disabled={isValidating}
                      className="flex items-center gap-1 px-3 py-1 text-sm bg-accent hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50"
                    >
                      <Play className="w-4 h-4" />
                      {isValidating ? 'Validating...' : 'Validate'}
                    </button>
                  </div>
                </div>

                {/* Editor + Validation Status */}
                <div className="flex-1 flex min-h-0">
                  <div className="flex-1 p-4 min-h-0">
                    <div className="h-full max-h-[calc(100vh-280px)]">
                      <Editor
                        value={content}
                        onChange={setContent}
                        className="h-full"
                      />
                    </div>
                  </div>

                  {/* Validation Status Panel */}
                  <div className="w-72 border-l border-border p-4 overflow-auto bg-surface/30">
                    <h3 className="text-sm font-semibold mb-3">Validation Status</h3>

                    {isValidating && (
                      <div className="flex items-center gap-2 text-accent">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Validating...
                      </div>
                    )}

                    {!isValidating && validationResult && (
                      <div className="space-y-3">
                        {isValid ? (
                          <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                            <Check className="w-5 h-5" />
                            <span className="font-medium">Valid PSDL</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
                            <AlertCircle className="w-5 h-5" />
                            <span className="font-medium">{errorCount} Error{errorCount !== 1 ? 's' : ''}</span>
                          </div>
                        )}

                        {warningCount > 0 && (
                          <div className="flex items-center gap-2 text-yellow-600 dark:text-yellow-400 text-sm">
                            <AlertCircle className="w-4 h-4" />
                            {warningCount} Warning{warningCount !== 1 ? 's' : ''}
                          </div>
                        )}

                        {/* Errors */}
                        {validationResult.errors.length > 0 && (
                          <div className="mt-3">
                            <h4 className="text-xs font-semibold text-red-600 dark:text-red-400 uppercase mb-2">Errors</h4>
                            <div className="space-y-1 max-h-40 overflow-auto">
                              {validationResult.errors.map((err, i) => (
                                <div key={i} className="text-xs text-red-700 dark:text-red-300 bg-red-100 dark:bg-red-900/20 p-2 rounded">
                                  {err.line && <span className="text-red-600 dark:text-red-400">Line {err.line}: </span>}
                                  {err.message}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Warnings */}
                        {validationResult.warnings.length > 0 && (
                          <div className="mt-3">
                            <h4 className="text-xs font-semibold text-yellow-600 dark:text-yellow-400 uppercase mb-2">Warnings</h4>
                            <div className="space-y-1 max-h-40 overflow-auto">
                              {validationResult.warnings.map((warn, i) => (
                                <div key={i} className="text-xs text-yellow-700 dark:text-yellow-300 bg-yellow-100 dark:bg-yellow-900/20 p-2 rounded">
                                  {warn.line && <span className="text-yellow-600 dark:text-yellow-400">Line {warn.line}: </span>}
                                  {warn.message}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {!isValidating && !validationResult && (
                      <p className="text-sm text-muted">
                        Click &quot;Validate&quot; to check your scenario
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* LLM Mode: Generation Panel */}
            {inputMode === 'llm' && (
              <div className="flex-1 overflow-auto">
                <GenerationPanel onUseGenerated={handleUseGenerated} />
              </div>
            )}
          </div>
        )}

        {/* Step 2: DAG Preview */}
        {currentStep === 'preview' && (
          <div className="h-full flex flex-col" style={{ height: 'calc(100vh - 140px)' }}>
            <div className="p-4 border-b border-border bg-surface/30 flex-shrink-0">
              <h2 className="text-lg font-semibold">Scenario DAG</h2>
              <p className="text-sm text-muted">
                Visual representation of signals, trends, and logic rules
              </p>
            </div>
            <div className="flex-1" style={{ minHeight: '500px' }}>
              <DAGView outline={outlineResult} />
            </div>
          </div>
        )}

        {/* Step 3: Export (Governance + Export combined) */}
        {currentStep === 'export' && (
          <div className="h-full overflow-auto p-6">
            <div className="max-w-3xl mx-auto">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left Column: Governance / IRB Documentation */}
                <div className="space-y-4">
                  <div>
                    <h2 className="text-lg font-semibold flex items-center gap-2">
                      <Shield className="w-5 h-5" />
                      IRB Documentation
                    </h2>
                    <p className="text-sm text-muted mt-1">
                      Optional governance notes for clinical review
                    </p>
                  </div>

                  {/* Scenario Info (compact) */}
                  <div className="bg-surface rounded-lg p-3 border border-border text-sm space-y-1">
                    <div className="flex justify-between">
                      <span className="text-muted">Scenario:</span>
                      <span className="font-semibold">{outlineResult?.scenario || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted">Signals:</span>
                      <span className="text-blue-600 dark:text-blue-400">{outlineResult?.signals?.length || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted">Rules:</span>
                      <span className="text-green-600 dark:text-green-400">{outlineResult?.logic?.length || 0}</span>
                    </div>
                  </div>

                  {/* Documentation Fields */}
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium mb-1.5">Clinical Summary</label>
                      <textarea
                        value={governanceData.clinicalSummary}
                        onChange={(e) => setGovernanceData({ ...governanceData, clinicalSummary: e.target.value })}
                        placeholder="What does this algorithm detect and why?"
                        className="w-full h-20 px-3 py-2 text-sm bg-surface border border-border rounded-lg text-foreground placeholder-muted focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1.5">Justification</label>
                      <textarea
                        value={governanceData.justification}
                        onChange={(e) => setGovernanceData({ ...governanceData, justification: e.target.value })}
                        placeholder="Why is this algorithm needed?"
                        className="w-full h-20 px-3 py-2 text-sm bg-surface border border-border rounded-lg text-foreground placeholder-muted focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1.5">Risk Assessment</label>
                      <textarea
                        value={governanceData.riskAssessment}
                        onChange={(e) => setGovernanceData({ ...governanceData, riskAssessment: e.target.value })}
                        placeholder="What are the risks of false positives/negatives?"
                        className="w-full h-20 px-3 py-2 text-sm bg-surface border border-border rounded-lg text-foreground placeholder-muted focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                      />
                    </div>
                  </div>
                </div>

                {/* Right Column: Export Bundle */}
                <div className="space-y-4">
                  <div>
                    <h2 className="text-lg font-semibold flex items-center gap-2">
                      <Download className="w-5 h-5" />
                      Export Bundle
                    </h2>
                    <p className="text-sm text-muted mt-1">
                      Download certified scenario bundle
                    </p>
                  </div>

                  {exportResult ? (
                    <div className="bg-surface border border-border rounded-lg p-4 space-y-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-green-100 dark:bg-green-900/50 rounded-lg flex items-center justify-center">
                          <FileText className="w-5 h-5 text-green-600 dark:text-green-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-sm truncate">{outlineResult?.scenario || 'scenario'}.json</h3>
                          <p className="text-xs text-muted">Certified Bundle</p>
                        </div>
                      </div>

                      <div className="border-t border-border pt-3">
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div className="flex items-center gap-1.5">
                            <Check className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
                            <span>Scenario Definition</span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <Check className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
                            <span>Canonical Form</span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <Check className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
                            <span>Content Hash</span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <Check className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
                            <span>Validation Proof</span>
                          </div>
                        </div>
                      </div>

                      <div className="border-t border-border pt-3">
                        <div className="bg-background rounded p-2 text-xs font-mono space-y-0.5">
                          <div className="text-muted">Version: {exportResult.bundle_version}</div>
                          <div className="text-muted">Certified: {new Date(exportResult.certified_at).toLocaleDateString()}</div>
                          <div className="text-muted truncate">Hash: {exportResult.checksum?.substring(0, 24)}...</div>
                        </div>
                      </div>

                      <ExportButton
                        exportData={exportResult}
                        scenarioName={outlineResult?.scenario || 'scenario'}
                        isLoading={isLoadingExport}
                      />
                    </div>
                  ) : (
                    <div className="bg-surface border border-border rounded-lg p-6 text-center">
                      <AlertCircle className="w-10 h-10 text-muted mx-auto mb-2" />
                      <p className="text-muted text-sm">No export data available</p>
                      <p className="text-xs text-muted mt-1">Validate your scenario first</p>
                    </div>
                  )}

                  {/* IRB Word Export */}
                  <GovernancePanel
                    outline={outlineResult}
                    governanceData={governanceData}
                    onGovernanceChange={setGovernanceData}
                    content={content}
                    isLoading={isLoadingOutline}
                    compactMode
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Full Screen Editor Modal */}
      {showFullEditor && (
        <div className="fixed inset-0 z-50 bg-background flex flex-col">
          <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface">
            <span className="text-sm font-medium">Full Editor</span>
            <div className="flex items-center gap-2">
              <button
                onClick={handleValidate}
                disabled={isValidating}
                className="flex items-center gap-1 px-3 py-1 text-sm bg-accent hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50"
              >
                <Play className="w-4 h-4" />
                {isValidating ? 'Validating...' : 'Validate'}
              </button>
              <button
                onClick={() => setShowFullEditor(false)}
                className="p-1.5 hover:bg-surface-hover rounded transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
          <div className="flex-1 p-4">
            <Editor
              value={content}
              onChange={setContent}
              className="h-full"
            />
          </div>
        </div>
      )}
    </div>
  );
}
