'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  FileUp, Play, RefreshCw, ChevronRight, ChevronLeft,
  Check, AlertCircle, Loader2, Edit3, Sparkles,
  Download, Eye, FileText, Shield, Maximize2, X,
  Github, Package, Heart, ExternalLink, HelpCircle, Gauge
} from 'lucide-react';
import { Editor, DAGView, GovernancePanel, ExportButton, GenerationPanel, ThemeToggle, Logo } from '@/components';
import MedsPreviewCard from '@/components/MedsPreviewCard';
import PrepareStep from '@/components/PrepareStep';
import { PSDLBuilder } from '@/components/builder';
import WelcomeGuide, { useWelcomeGuide } from '@/components/WelcomeGuide';
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

type WizardStep = 'input' | 'preview' | 'export' | 'prepare';
type InputMode = 'builder' | 'llm' | 'manual';

interface StepInfo {
  id: WizardStep;
  label: string;
  icon: React.ReactNode;
}

const STEPS: StepInfo[] = [
  { id: 'input', label: 'Input', icon: <Edit3 className="w-4 h-4" /> },
  { id: 'preview', label: 'Preview', icon: <Eye className="w-4 h-4" /> },
  { id: 'export', label: 'Export', icon: <Download className="w-4 h-4" /> },
  { id: 'prepare', label: 'Prepare', icon: <Gauge className="w-4 h-4" /> },
];

export default function Home() {
  // Wizard state
  const [currentStep, setCurrentStep] = useState<WizardStep>('input');
  const [inputMode, setInputMode] = useState<InputMode>('builder');

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
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [transitionMessage, setTransitionMessage] = useState('');

  // Error state
  const [apiError, setApiError] = useState<string | null>(null);

  // UI state
  const [showFullEditor, setShowFullEditor] = useState(false);
  const [showAnnouncement, setShowAnnouncement] = useState(true);

  // Welcome guide
  const { isOpen: showWelcomeGuide, closeGuide, openGuide } = useWelcomeGuide();

  // Governance data
  const [governanceData, setGovernanceData] = useState({
    clinicalSummary: '',
    justification: '',
    riskAssessment: '',
  });

  const handleValidate = useCallback(async (showTransition = false): Promise<{ valid: boolean; errors: string[] }> => {
    if (!content.trim()) return { valid: false, errors: ['No scenario content to validate'] };

    setIsValidating(true);
    setIsLoadingOutline(true);
    setIsLoadingExport(true);
    setApiError(null);

    if (showTransition) {
      setIsTransitioning(true);
      setTransitionMessage('Validating scenario...');
    }

    try {
      const validation = await api.validate(content);
      setValidationResult(validation);

      if (validation.valid) {
        if (showTransition) {
          setTransitionMessage('Generating preview data...');
        }
        const [outline, exportData] = await Promise.all([
          api.getOutline(content),
          api.exportBundle({ content }),
        ]);
        setOutlineResult(outline);
        setExportResult(exportData);
        return { valid: true, errors: [] };
      } else {
        setOutlineResult(null);
        setExportResult(null);
        const errorMessages = validation.errors?.map(e => e.message) || ['Validation failed'];
        return { valid: false, errors: errorMessages };
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'API request failed';
      setApiError(errorMsg);
      setValidationResult(null);
      setOutlineResult(null);
      setExportResult(null);
      return { valid: false, errors: [errorMsg] };
    } finally {
      setIsValidating(false);
      setIsLoadingOutline(false);
      setIsLoadingExport(false);
      setIsTransitioning(false);
      setTransitionMessage('');
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
    const stepOrder: WizardStep[] = ['input', 'preview', 'export', 'prepare'];
    const currentIndex = stepOrder.indexOf(currentStep);
    if (currentIndex < stepOrder.length - 1) {
      goToStep(stepOrder[currentIndex + 1]);
    }
  };

  const goBack = () => {
    const stepOrder: WizardStep[] = ['input', 'preview', 'export', 'prepare'];
    const currentIndex = stepOrder.indexOf(currentStep);
    if (currentIndex > 0) {
      setCurrentStep(stepOrder[currentIndex - 1]);
    }
  };

  // Step status for indicators
  const getStepStatus = (step: WizardStep): 'complete' | 'current' | 'upcoming' | 'error' => {
    const stepOrder: WizardStep[] = ['input', 'preview', 'export', 'prepare'];
    const currentIndex = stepOrder.indexOf(currentStep);
    const stepIndex = stepOrder.indexOf(step);

    if (step === 'input' && hasErrors) return 'error';
    if (stepIndex < currentIndex) return 'complete';
    if (stepIndex === currentIndex) return 'current';
    return 'upcoming';
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col transition-colors">
      {/* Announcement Bar */}
      {showAnnouncement && (
        <div className="bg-gradient-to-r from-accent-purple to-accent-cyan text-white px-4 py-2 text-center text-sm relative">
          <span className="font-medium">Open Source Clinical Algorithm Tool</span>
          <span className="mx-2 opacity-60">|</span>
          <span className="opacity-90">Try PSDL for standardized patient scenario definitions</span>
          <a
            href="https://github.com/Chesterguan/PSDL"
            target="_blank"
            rel="noopener noreferrer"
            className="ml-2 inline-flex items-center gap-1 underline underline-offset-2 hover:opacity-80 font-medium"
          >
            Learn more <ExternalLink className="w-3 h-3" />
          </a>
          <button
            onClick={() => setShowAnnouncement(false)}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-white/20 rounded transition-colors"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Unified Header */}
      <header className="sticky top-0 z-10 px-6 py-3 bg-background/95 backdrop-blur-sm border-b border-border/50">
        <div className="flex items-center justify-between">
          {/* Left: Logo + Nav */}
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2.5">
              <Logo size={32} />
              <div className="flex flex-col">
                <span className="text-lg font-bold text-foreground tracking-tight leading-tight">PSDL Inspector</span>
                <span className="text-[10px] text-muted leading-tight hidden sm:block">Validate & visualize clinical algorithms</span>
              </div>
            </div>

            {/* Step Navigation - Workflow Pills */}
            <div className="flex items-center">
              <div className="flex items-center bg-background-tertiary/50 rounded-full px-1 py-1 border border-border/50">
                {currentStep !== 'input' && (
                  <button
                    onClick={goBack}
                    aria-label="Previous step"
                    className="p-1 rounded-full hover:bg-background text-muted hover:text-foreground transition-colors mr-1"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                  </button>
                )}
                {STEPS.map((step, index) => {
                  const status = getStepStatus(step.id);
                  const isClickable = status === 'complete' || status === 'current' || (step.id === 'input');
                  return (
                    <div key={step.id} className="flex items-center">
                      {index > 0 && (
                        <div className={`w-6 h-px mx-0.5 ${
                          status === 'complete' ? 'bg-accent-success/50' :
                          status === 'current' ? 'bg-accent-purple/30' :
                          'bg-border'
                        }`} />
                      )}
                      <button
                        onClick={() => isClickable && goToStep(step.id)}
                        disabled={!isClickable}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                          status === 'current'
                            ? 'bg-gradient-to-r from-accent-purple to-accent-cyan text-white shadow-sm'
                            : status === 'complete'
                            ? 'bg-accent-success/10 text-accent-success hover:bg-accent-success/20'
                            : status === 'error'
                            ? 'bg-accent-danger/10 text-accent-danger'
                            : 'text-muted hover:text-foreground-secondary hover:bg-background/50'
                        }`}
                      >
                        {status === 'complete' ? (
                          <Check className="w-3 h-3" />
                        ) : status === 'error' ? (
                          <AlertCircle className="w-3 h-3" />
                        ) : (
                          <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${
                            status === 'current' ? 'bg-white/20' : 'bg-current/10'
                          }`}>
                            {index + 1}
                          </span>
                        )}
                        {step.label}
                      </button>
                    </div>
                  );
                })}
                {currentStep !== 'prepare' && canProceed && (
                  <button
                    onClick={goNext}
                    aria-label="Next step"
                    className="p-1 rounded-full hover:bg-background text-muted hover:text-foreground transition-colors ml-1"
                  >
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Right: Links + Theme + Version */}
          <div className="flex items-center gap-2">
            {/* External Links */}
            <div className="flex items-center gap-1 mr-2">
              <a
                href="https://github.com/Chesterguan/psdl-inspector"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-lg hover:bg-background-tertiary text-muted hover:text-foreground transition-colors"
                title="GitHub Repository"
              >
                <Github className="w-5 h-5" />
              </a>
              <a
                href="https://github.com/Chesterguan/PSDL/blob/main/docs/WHITEPAPER.md"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-lg hover:bg-background-tertiary text-muted hover:text-foreground transition-colors"
                title="PSDL Whitepaper"
              >
                <FileText className="w-5 h-5" />
              </a>
              <a
                href="https://pypi.org/project/psdl-lang/"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-lg hover:bg-background-tertiary text-muted hover:text-foreground transition-colors"
                title="psdl-lang on PyPI"
              >
                <Package className="w-5 h-5" />
              </a>
              <a href="/catalog" title="Institutional Data Catalog" className="flex items-center gap-1.5 text-sm text-muted hover:text-foreground transition-colors">
                <Package className="w-4 h-4" /> Data Catalog
              </a>
              <a href="/preflight" title="SQL Preflight — cost & risk check before you run" className="flex items-center gap-1.5 text-sm text-muted hover:text-foreground transition-colors">
                <Gauge className="w-4 h-4" /> Preflight
              </a>
            </div>
            {versionInfo && (
              <span className="text-[10px] text-muted font-mono hidden sm:block">v{versionInfo.psdl_lang}</span>
            )}
            <button
              onClick={openGuide}
              className="p-2 hover:bg-background-secondary rounded-lg transition-colors text-muted hover:text-foreground"
              title="Help & Guide"
            >
              <HelpCircle className="w-4 h-4" />
            </button>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Transition Overlay */}
      {isTransitioning && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center">
          <div className="bg-background-secondary rounded-2xl p-8 shadow-xl border border-border/50 text-center max-w-sm mx-4">
            <div className="relative w-16 h-16 mx-auto mb-4">
              <div className="absolute inset-0 rounded-full border-4 border-accent/20"></div>
              <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-accent animate-spin"></div>
              <Loader2 className="absolute inset-3 w-10 h-10 text-accent animate-pulse" />
            </div>
            <p className="text-lg font-semibold text-foreground mb-2">Processing</p>
            <p className="text-sm text-foreground-secondary">{transitionMessage}</p>
            <div className="mt-4 h-1 bg-background-tertiary rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-accent-purple to-accent-cyan animate-pulse" style={{ width: '60%' }}></div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 overflow-auto p-6">
        <div className="workbench">
        {apiError && (
          <div className="mb-4 p-3 bg-accent-danger/10 rounded-lg text-accent-danger text-sm">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="font-semibold block mb-1">Validation Error:</strong>
                <ul className="list-disc list-inside space-y-0.5">
                  {apiError.split('\n').map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Step 1: Input */}
        {currentStep === 'input' && (
          <div>
            {/* Mode Tabs + Validate in one row */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex p-0.5 bg-background-secondary rounded-lg">
                <button
                  onClick={() => setInputMode('builder')}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    inputMode === 'builder' ? 'bg-accent text-white' : 'text-foreground-secondary hover:text-foreground'
                  }`}
                >
                  <FileText className="w-4 h-4" />
                  Builder
                </button>
                <button
                  onClick={() => setInputMode('llm')}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    inputMode === 'llm' ? 'bg-accent-purple text-white' : 'text-foreground-secondary hover:text-foreground'
                  }`}
                >
                  <Sparkles className="w-4 h-4" />
                  AI Generate
                </button>
                <button
                  onClick={() => setInputMode('manual')}
                  className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    inputMode === 'manual' ? 'bg-accent-cyan text-white' : 'text-foreground-secondary hover:text-foreground'
                  }`}
                >
                  <Edit3 className="w-4 h-4" />
                  Raw YAML
                </button>
              </div>

{/* Validate button only shown in manual mode - Builder uses Continue button */}
            </div>

            {/* Builder Mode: Constrained PSDL Builder */}
            {inputMode === 'builder' && (
              <PSDLBuilder
                onYamlChange={(yaml) => {
                  setContent(yaml);
                  // Clear validation when YAML changes
                  setValidationResult(null);
                  setOutlineResult(null);
                  setExportResult(null);
                }}
onContinue={async () => {
                  // Validate with transition animation and navigate to preview if valid
                  setApiError(null);
                  const result = await handleValidate(true);
                  if (result.valid) {
                    setCurrentStep('preview');
                  } else {
                    // Show specific validation errors
                    setApiError(result.errors.join('\n'));
                  }
                }}
                isValidating={isValidating}
              />
            )}

            {/* Manual Mode: Raw YAML Editor */}
            {inputMode === 'manual' && (
              <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_340px] xl:grid-cols-[minmax(0,1fr)_400px] gap-6">
                {/* Left: YAML Editor */}
                <div className="space-y-4">
                  {/* Section 1: Editor */}
                  <div className="section-panel bg-background-secondary rounded-lg overflow-hidden">
                    <div className="section-header flex items-center justify-between px-4 py-3">
                      <div className="flex items-center gap-3">
                        <span className="section-number font-mono text-sm font-semibold text-accent-cyan">01</span>
                        <span className="section-title text-sm font-medium text-foreground">YAML Editor</span>
                        {content.split('\n').length > 50 && (
                          <span className="text-xs text-muted bg-background px-2 py-0.5 rounded font-mono">
                            {content.split('\n').length} lines
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setShowFullEditor(true)}
                          className="p-2 hover:bg-background rounded-md transition-colors"
                          title="Expand editor"
                        >
                          <Maximize2 className="w-4 h-4 text-foreground-secondary" />
                        </button>
                        <label className="flex items-center gap-1.5 px-3 py-2 bg-background hover:bg-background-tertiary text-foreground text-sm font-medium rounded-md cursor-pointer transition-colors">
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
                          className="flex items-center gap-1.5 px-3 py-2 bg-background hover:bg-background-tertiary text-foreground text-sm font-medium rounded-md transition-colors"
                        >
                          <RefreshCw className="w-4 h-4" />
                          <span className="hidden sm:inline">Reset</span>
                        </button>
                      </div>
                    </div>
                    <div className="section-body px-4 pb-4">
                      <div className="h-[calc(100vh-360px)] min-h-[400px]">
                        <Editor
                          value={content}
                          onChange={setContent}
                          className="h-full"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Validate Button */}
                  <div className="flex items-center gap-4">
                    <button
                      onClick={() => handleValidate()}
                      disabled={isValidating || !content.trim()}
                      className={`flex items-center gap-2 px-5 py-3 rounded-lg font-medium text-sm transition-colors ${
                        !isValidating && content.trim()
                          ? 'bg-accent-cyan hover:bg-accent-cyan/90 text-white cursor-pointer'
                          : 'bg-background-tertiary text-muted cursor-not-allowed'
                      }`}
                    >
                      {isValidating ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Validating...
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4" />
                          Validate Scenario
                        </>
                      )}
                    </button>

                    {/* Status Indicator */}
                    {validationResult && !isValidating && (
                      <span className={`text-sm font-medium ${isValid ? 'text-accent-success' : 'text-accent-danger'}`}>
                        {isValid ? 'Valid PSDL' : `${errorCount} error${errorCount !== 1 ? 's' : ''} found`}
                      </span>
                    )}
                  </div>
                </div>

                {/* Right: Validation Panel */}
                <div className="preview-panel bg-background-secondary rounded-lg sticky top-20 max-h-[calc(100vh-120px)] flex flex-col overflow-hidden">
                  {/* Header */}
                  <div className="px-4 py-3 flex items-center justify-between border-b border-border/30">
                    <span className="text-sm font-semibold text-foreground uppercase tracking-wide">Validation</span>
                    {validationResult && (
                      <div className="flex items-center gap-2">
                        {isValid ? (
                          <span className="flex items-center gap-1 text-accent-success text-sm font-medium">
                            <Check className="w-4 h-4" /> Valid
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-accent-danger text-sm font-medium">
                            <AlertCircle className="w-4 h-4" /> {errorCount} issue{errorCount !== 1 ? 's' : ''}
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 overflow-y-auto px-4 py-4">
                    {isValidating && (
                      <div className="h-full flex flex-col items-center justify-center text-center py-12">
                        <Loader2 className="w-10 h-10 text-accent-cyan animate-spin mb-4" />
                        <p className="text-sm text-foreground">Validating PSDL...</p>
                        <p className="text-sm text-foreground-secondary mt-1">Checking syntax and semantics</p>
                      </div>
                    )}

                    {!isValidating && !validationResult && (
                      <div className="h-full flex flex-col items-center justify-center text-center py-12">
                        <Play className="w-10 h-10 text-accent-cyan/30 mb-4" />
                        <p className="text-sm text-foreground-secondary">Click Validate to check your scenario</p>
                        <p className="text-sm text-muted mt-1">Syntax and semantic validation</p>
                      </div>
                    )}

                    {!isValidating && validationResult && (
                      <div className="space-y-4">
                        {/* Status Badge */}
                        {isValid ? (
                          <div className="flex items-center gap-3 text-accent-success p-4 bg-accent-success/10 rounded-lg border border-accent-success/20">
                            <Check className="w-5 h-5" />
                            <div>
                              <span className="font-semibold text-sm">Valid PSDL</span>
                              <p className="text-sm opacity-80">Ready for preview</p>
                            </div>
                          </div>
                        ) : (
                          <div className="flex items-center gap-3 text-accent-danger p-4 bg-accent-danger/10 rounded-lg border border-accent-danger/20">
                            <AlertCircle className="w-5 h-5" />
                            <div>
                              <span className="font-semibold text-sm">{errorCount} Error{errorCount !== 1 ? 's' : ''}</span>
                              <p className="text-sm opacity-80">Fix issues to continue</p>
                            </div>
                          </div>
                        )}

                        {/* Warnings */}
                        {warningCount > 0 && (
                          <div className="flex items-center gap-2 text-accent-warning text-sm p-3 bg-accent-warning/10 rounded-lg border border-accent-warning/20">
                            <AlertCircle className="w-4 h-4" />
                            {warningCount} Warning{warningCount !== 1 ? 's' : ''}
                          </div>
                        )}

                        {/* Errors */}
                        {validationResult.errors.length > 0 && (
                          <div className="p-3 bg-accent-danger/10 rounded-lg border border-accent-danger/20">
                            <h4 className="text-sm font-semibold text-accent-danger mb-2">Errors</h4>
                            <ul className="text-sm text-accent-danger space-y-1.5 max-h-48 overflow-y-auto">
                              {validationResult.errors.map((err, i) => (
                                <li key={i} className="flex gap-2">
                                  <span className="flex-shrink-0">-</span>
                                  <span>
                                    {err.line && <span className="font-mono text-sm opacity-75">L{err.line}: </span>}
                                    {err.message}
                                  </span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Warnings */}
                        {validationResult.warnings.length > 0 && (
                          <div className="p-3 bg-accent-warning/10 rounded-lg border border-accent-warning/20">
                            <h4 className="text-sm font-semibold text-accent-warning mb-2">Warnings</h4>
                            <ul className="text-sm text-accent-warning space-y-1.5 max-h-48 overflow-y-auto">
                              {validationResult.warnings.map((warn, i) => (
                                <li key={i} className="flex gap-2">
                                  <span className="flex-shrink-0">-</span>
                                  <span>
                                    {warn.line && <span className="font-mono text-sm opacity-75">L{warn.line}: </span>}
                                    {warn.message}
                                  </span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  {isValid && outlineResult && (
                    <div className="flex gap-2 p-3 border-t border-border/30">
                      <button
                        onClick={() => setCurrentStep('preview')}
                        className="flex-1 py-2.5 px-3 bg-accent hover:bg-accent-hover text-white text-sm font-medium rounded-md transition-colors"
                      >
                        Continue to Preview
                      </button>
                    </div>
                  )}

                  {/* Tip */}
                  <div className="px-4 pb-4">
                    <div className="p-3 bg-accent-cyan/5 rounded-lg border border-accent-cyan/10">
                      <p className="text-sm text-foreground-secondary">
                        <span className="font-semibold text-accent-cyan">Tip:</span> Upload a .yaml file or paste PSDL directly
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* LLM Mode: Generation Panel */}
            {inputMode === 'llm' && (
              <div className="flex-1 overflow-auto">
                <GenerationPanel
                  onUseGenerated={handleUseGenerated}
                  onContinue={async (yaml) => {
                    setContent(yaml);
                    setIsLoadingOutline(true);
                    setIsLoadingExport(true);
                    setIsTransitioning(true);
                    setTransitionMessage('Generating preview data...');
                    try {
                      const [outline, exportData] = await Promise.all([
                        api.getOutline(yaml),
                        api.exportBundle({ content: yaml }),
                      ]);
                      setOutlineResult(outline);
                      setExportResult(exportData);
                      setValidationResult({ valid: true, errors: [], warnings: [], parsed: null });
                      setCurrentStep('preview');
                    } catch (error) {
                      setApiError(error instanceof Error ? error.message : 'Failed to load preview data');
                    } finally {
                      setIsLoadingOutline(false);
                      setIsLoadingExport(false);
                      setIsTransitioning(false);
                      setTransitionMessage('');
                    }
                  }}
                />
              </div>
            )}
          </div>
        )}

        {/* Step 2: DAG Preview */}
        {currentStep === 'preview' && (
          <div className="h-full flex flex-col" style={{ height: 'calc(100vh - 160px)' }}>
            <div className="p-6 border-b border-border bg-background-secondary/50 flex-shrink-0">
              <h2 className="text-lg font-semibold">Scenario DAG</h2>
              <p className="text-sm text-muted mt-1">
                Visual representation of signals, trends, and logic rules
              </p>
            </div>
            <div className="flex-1" style={{ minHeight: '400px' }}>
              <DAGView outline={outlineResult} />
            </div>
            {/* Navigation Bar */}
            <div className="p-4 border-t border-border bg-background-secondary/50 flex-shrink-0">
              <div className="flex items-center justify-between max-w-4xl mx-auto">
                <button
                  onClick={() => setCurrentStep('input')}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-foreground-secondary hover:text-foreground transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Back to Input
                </button>
                <div className="flex items-center gap-3">
                  <div className="text-sm text-muted">
                    {outlineResult && (
                      <span>
                        {outlineResult.signals?.length || 0} signals, {outlineResult.trends?.length || 0} trends, {outlineResult.logic?.length || 0} rules
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => setCurrentStep('export')}
                    className="flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent-hover text-white rounded-lg font-medium text-sm transition-colors"
                  >
                    Continue to Export
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Export (Governance + Export combined) */}
        {currentStep === 'export' && (
          <div className="h-full overflow-auto p-8">
            <div className="max-w-4xl mx-auto">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Left Column: Governance / IRB Documentation */}
                <div className="space-y-6">
                  <div>
                    <h2 className="text-xl font-semibold flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-accent-cyan/15 flex items-center justify-center">
                        <Shield className="w-5 h-5 text-accent-cyan" />
                      </div>
                      IRB Documentation
                    </h2>
                    <p className="text-sm text-muted mt-2 ml-13">
                      Optional governance notes for clinical review
                    </p>
                  </div>

                  {/* Scenario Info (compact) */}
                  <div className="bg-surface rounded-xl p-4 border border-border space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted">Scenario</span>
                      <span className="font-semibold font-mono text-sm">{outlineResult?.scenario || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted">Signals</span>
                      <span className="badge badge-info">{outlineResult?.signals?.length || 0}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted">Rules</span>
                      <span className="badge badge-success">{outlineResult?.logic?.length || 0}</span>
                    </div>
                  </div>

                  {/* Documentation Fields */}
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">Clinical Summary</label>
                      <textarea
                        value={governanceData.clinicalSummary}
                        onChange={(e) => setGovernanceData({ ...governanceData, clinicalSummary: e.target.value })}
                        placeholder="What does this algorithm detect and why?"
                        className="input h-24 resize-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">Justification</label>
                      <textarea
                        value={governanceData.justification}
                        onChange={(e) => setGovernanceData({ ...governanceData, justification: e.target.value })}
                        placeholder="Why is this algorithm needed?"
                        className="input h-24 resize-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">Risk Assessment</label>
                      <textarea
                        value={governanceData.riskAssessment}
                        onChange={(e) => setGovernanceData({ ...governanceData, riskAssessment: e.target.value })}
                        placeholder="What are the risks of false positives/negatives?"
                        className="input h-24 resize-none"
                      />
                    </div>
                  </div>
                </div>

                {/* Right Column: Export Bundle */}
                <div className="space-y-6">
                  <div>
                    <h2 className="text-xl font-semibold flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-accent-success/15 flex items-center justify-center">
                        <Download className="w-5 h-5 text-accent-success" />
                      </div>
                      Export Bundle
                    </h2>
                    <p className="text-sm text-muted mt-2 ml-13">
                      Download certified scenario bundle
                    </p>
                  </div>

                  {exportResult ? (
                    <div className="bg-surface border border-border rounded-xl p-5 space-y-5">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-accent-success/15 rounded-xl flex items-center justify-center">
                          <FileText className="w-6 h-6 text-accent-success" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold truncate">{outlineResult?.scenario || 'scenario'}.json</h3>
                          <p className="text-sm text-muted">Certified Bundle</p>
                        </div>
                      </div>

                      <div className="border-t border-border pt-4">
                        <div className="grid grid-cols-2 gap-3 text-sm">
                          <div className="flex items-center gap-2">
                            <Check className="w-4 h-4 text-accent-success" />
                            <span>Scenario Definition</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Check className="w-4 h-4 text-accent-success" />
                            <span>Canonical Form</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Check className="w-4 h-4 text-accent-success" />
                            <span>Content Hash</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Check className="w-4 h-4 text-accent-success" />
                            <span>Validation Proof</span>
                          </div>
                        </div>
                      </div>

                      <div className="border-t border-border pt-4">
                        <div className="bg-background-secondary rounded-lg p-3 text-sm font-mono space-y-1">
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
                    <div className="bg-surface border border-border rounded-xl p-8 text-center">
                      <AlertCircle className="w-12 h-12 text-muted mx-auto mb-3" />
                      <p className="text-muted font-medium">No export data available</p>
                      <p className="text-sm text-muted mt-1">Validate your scenario first</p>
                    </div>
                  )}

                  {/* MEDS Preview */}
                  <MedsPreviewCard
                    yaml={content}
                    signalCount={outlineResult?.signals?.length ?? 0}
                  />

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

        {/* Step 4: Prepare for execution (Data Catalog + Preflight) */}
        {currentStep === 'prepare' && (
          <div className="max-w-5xl mx-auto px-6 py-8">
            <PrepareStep />
          </div>
        )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50 bg-background-secondary/30 px-6 py-4">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-muted">
          <div className="flex items-center gap-1">
            <span>Built with</span>
            <Heart className="w-3.5 h-3.5 text-accent-danger fill-accent-danger" />
            <span>for the clinical informatics community</span>
          </div>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com/Chesterguan/PSDL"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              PSDL Language
            </a>
            <span className="text-border">|</span>
            <a
              href="https://github.com/Chesterguan/psdl-inspector"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              Contribute
            </a>
            <span className="text-border">|</span>
            <a
              href="https://github.com/Chesterguan/PSDL/blob/main/docs/WHITEPAPER.md"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              Whitepaper
            </a>
          </div>
          <div className="text-xs opacity-70">
            MIT License {new Date().getFullYear()}
          </div>
        </div>
      </footer>

      {/* Full Screen Editor Modal */}
      {showFullEditor && (
        <div className="fixed inset-0 z-50 bg-background flex flex-col">
          <div className="flex items-center justify-between px-6 py-3 border-b border-border bg-surface">
            <span className="text-sm font-semibold">Full Editor</span>
            <div className="flex items-center gap-3">
              <button
                onClick={() => handleValidate()}
                disabled={isValidating}
                className="flex items-center gap-1.5 px-4 py-1.5 text-sm bg-accent hover:bg-accent-hover text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                <Play className="w-4 h-4" />
                {isValidating ? 'Validating...' : 'Validate'}
              </button>
              <button
                onClick={() => setShowFullEditor(false)}
                className="p-2 hover:bg-surface-hover rounded-lg transition-colors border border-border"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
          <div className="flex-1 p-6">
            <Editor
              value={content}
              onChange={setContent}
              className="h-full"
            />
          </div>
        </div>
      )}

      {/* Welcome Guide Modal */}
      <WelcomeGuide isOpen={showWelcomeGuide} onClose={closeGuide} />
    </div>
  );
}
