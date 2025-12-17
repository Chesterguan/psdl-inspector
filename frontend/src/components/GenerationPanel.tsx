'use client';

import { useState, useEffect, useRef } from 'react';
import { Sparkles, AlertCircle, CheckCircle, Loader2, RefreshCw, ChevronDown, ChevronRight, BookOpen, Cloud, Server } from 'lucide-react';

interface GeneratedResult {
  yaml: string;
  valid: boolean;
  errors: string[];
  warnings: string[];
}

interface GenerationPanelProps {
  onUseGenerated: (result: GeneratedResult) => void;
}

interface ProviderStatus {
  available: boolean;
  model: string | null;
  models?: string[];
}

interface GenerationStatus {
  openai: ProviderStatus;
  ollama: ProviderStatus;
  available: boolean;
  default_provider: string;
}

type Provider = 'openai' | 'ollama';
type GenerationPhase = 'idle' | 'generating' | 'validating' | 'correcting' | 'done' | 'error';

const PHASE_MESSAGES: Record<GenerationPhase, string> = {
  idle: '',
  generating: 'Generating scenario...',
  validating: 'Validating PSDL...',
  correcting: 'Fixing validation errors...',
  done: 'Complete',
  error: 'Generation failed',
};

export default function GenerationPanel({ onUseGenerated }: GenerationPanelProps) {
  const [prompt, setPrompt] = useState('');
  const [clinicalContext, setClinicalContext] = useState('');
  const [showContext, setShowContext] = useState(false);
  const [generatedYaml, setGeneratedYaml] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [phase, setPhase] = useState<GenerationPhase>('idle');
  const [phaseDetail, setPhaseDetail] = useState('');
  const [isValid, setIsValid] = useState<boolean | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [attempts, setAttempts] = useState<number>(1);
  const [status, setStatus] = useState<GenerationStatus | null>(null);
  const [provider, setProvider] = useState<Provider>('openai');
  const [selectedOllamaModel, setSelectedOllamaModel] = useState<string | null>(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8200';

  const checkStatus = async () => {
    try {
      const resp = await fetch(`${apiBase}/api/generate/status`);
      if (!resp.ok) throw new Error('Failed to check status');
      const data = await resp.json();
      setStatus(data);

      // Set default provider based on availability
      if (data.default_provider) {
        setProvider(data.default_provider as Provider);
      }

      // Set default Ollama model if available
      if (!selectedOllamaModel && data.ollama?.model) {
        setSelectedOllamaModel(data.ollama.model);
      }
    } catch {
      setStatus({
        openai: { available: false, model: null },
        ollama: { available: false, model: null, models: [] },
        available: false,
        default_provider: 'openai',
      });
    }
  };

  useEffect(() => {
    checkStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only check status on mount

  // Timer for elapsed time during generation
  useEffect(() => {
    if (isGenerating) {
      setElapsedTime(0);
      timerRef.current = setInterval(() => {
        setElapsedTime((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isGenerating]);

  const isProviderAvailable = (p: Provider): boolean => {
    if (!status) return false;
    return p === 'openai' ? status.openai.available : status.ollama.available;
  };

  const canGenerate = prompt.trim() && isProviderAvailable(provider) && !isGenerating;

  const handleGenerate = async () => {
    if (!canGenerate) return;

    setIsGenerating(true);
    setPhase('generating');
    setPhaseDetail('Sending request to LLM...');
    setGeneratedYaml(null);
    setErrors([]);
    setWarnings([]);
    setIsValid(null);
    setAttempts(1);

    try {
      const phaseTimer = setTimeout(() => {
        setPhaseDetail(provider === 'openai'
          ? 'GPT-4o-mini is generating...'
          : 'LLM is thinking... (larger models may take 30-60s)');
      }, 2000);

      const response = await fetch(`${apiBase}/api/generate/scenario`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          provider,
          model: provider === 'ollama' ? selectedOllamaModel : undefined,
          max_retries: 3,
          clinical_context: clinicalContext.trim() || undefined,
        }),
      });

      clearTimeout(phaseTimer);

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Generation failed');
      }

      setPhase('validating');
      setPhaseDetail('Processing response...');

      const data = await response.json();

      if (data.attempts > 1) {
        setPhase('correcting');
        setPhaseDetail(`Auto-corrected in ${data.attempts} attempts`);
      }

      setGeneratedYaml(data.yaml);
      setIsValid(data.valid);
      setErrors(data.errors || []);
      setWarnings(data.warnings || []);
      setAttempts(data.attempts || 1);
      setPhase('done');
      setPhaseDetail(data.valid ? 'Valid PSDL generated' : `${data.errors?.length || 0} issues remaining`);
    } catch (error) {
      setPhase('error');
      setPhaseDetail(error instanceof Error ? error.message : 'Unknown error');
      setErrors([error instanceof Error ? error.message : 'Unknown error']);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleUseThis = () => {
    if (generatedYaml) {
      onUseGenerated({
        yaml: generatedYaml,
        valid: isValid || false,
        errors: errors,
        warnings: warnings,
      });
    }
  };

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const contextCharCount = clinicalContext.length;
  const contextWarning = contextCharCount > 10000;

  return (
    <div className="h-full overflow-auto p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-lg font-semibold text-foreground">
          <Sparkles className="w-5 h-5 text-yellow-500 dark:text-yellow-400" />
          AI-Assisted Generation
        </div>
        <button
          onClick={checkStatus}
          className="p-1 hover:bg-surface-hover rounded"
          title="Refresh status"
          disabled={isGenerating}
        >
          <RefreshCw className="w-4 h-4 text-muted" />
        </button>
      </div>

      {/* Provider Selector */}
      <div className="flex items-center gap-2 p-3 bg-surface-hover rounded-lg">
        <span className="text-sm text-muted">Provider:</span>
        <div className="flex gap-2">
          {/* OpenAI Button */}
          <button
            onClick={() => setProvider('openai')}
            disabled={isGenerating || !status?.openai.available}
            className={`
              flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors
              ${provider === 'openai'
                ? 'bg-blue-600 text-white'
                : 'bg-surface hover:bg-border text-foreground'}
              ${!status?.openai.available ? 'opacity-50 cursor-not-allowed' : ''}
            `}
          >
            <Cloud className="w-4 h-4" />
            OpenAI
            {status?.openai.available && (
              <span className="text-xs opacity-70">{status.openai.model}</span>
            )}
          </button>

          {/* Ollama Button */}
          <button
            onClick={() => setProvider('ollama')}
            disabled={isGenerating || !status?.ollama.available}
            className={`
              flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors
              ${provider === 'ollama'
                ? 'bg-green-600 text-white'
                : 'bg-surface hover:bg-border text-foreground'}
              ${!status?.ollama.available ? 'opacity-50 cursor-not-allowed' : ''}
            `}
          >
            <Server className="w-4 h-4" />
            Ollama
          </button>
        </div>

        {/* Ollama Model Selector (shown when Ollama is selected) */}
        {provider === 'ollama' && status?.ollama.available && status.ollama.models && status.ollama.models.length > 0 && (
          <select
            value={selectedOllamaModel || ''}
            onChange={(e) => setSelectedOllamaModel(e.target.value)}
            className="text-sm bg-surface border border-border rounded px-2 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-green-500"
            disabled={isGenerating}
          >
            {status.ollama.models.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
        )}

        {/* Status Indicators */}
        <div className="ml-auto flex items-center gap-2 text-xs">
          {status?.openai.available ? (
            <span className="text-green-600 dark:text-green-400 flex items-center gap-1">
              <CheckCircle className="w-3 h-3" /> OpenAI
            </span>
          ) : (
            <span className="text-muted flex items-center gap-1">
              <AlertCircle className="w-3 h-3" /> OpenAI
            </span>
          )}
          {status?.ollama.available ? (
            <span className="text-green-600 dark:text-green-400 flex items-center gap-1">
              <CheckCircle className="w-3 h-3" /> Ollama
            </span>
          ) : (
            <span className="text-muted flex items-center gap-1">
              <AlertCircle className="w-3 h-3" /> Ollama
            </span>
          )}
        </div>
      </div>

      {/* No Provider Available Warning */}
      {status && !status.available && (
        <div className="bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700 rounded-lg p-4 text-sm">
          <h4 className="font-semibold text-yellow-800 dark:text-yellow-300 mb-2">No LLM Provider Available</h4>
          <p className="text-yellow-700 dark:text-yellow-200/80 mb-2">
            Configure at least one provider:
          </p>
          <pre className="bg-surface p-2 rounded text-xs text-foreground overflow-x-auto">
{`# Option 1: OpenAI (recommended)
export OPENAI_API_KEY="sk-..."

# Option 2: Local Ollama
brew install ollama
ollama serve
ollama pull mistral-small`}
          </pre>
        </div>
      )}

      {/* Prompt Input */}
      <div>
        <label className="block text-sm font-medium text-foreground mb-2">
          Describe your clinical scenario
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Example: Detect early sepsis in ICU patients using temperature, heart rate, respiratory rate, and white blood cell count. Alert when multiple SIRS criteria are met."
          className="w-full h-28 px-3 py-2 bg-surface border border-border rounded-lg text-foreground placeholder-muted focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          disabled={!status?.available || isGenerating}
        />
      </div>

      {/* Clinical Context (Collapsible) */}
      <div className="border border-border rounded-lg overflow-hidden">
        <button
          onClick={() => setShowContext(!showContext)}
          className="w-full flex items-center justify-between px-3 py-2 bg-surface-hover hover:bg-border transition-colors text-sm"
          disabled={isGenerating}
        >
          <div className="flex items-center gap-2 text-foreground">
            <BookOpen className="w-4 h-4" />
            <span>Clinical Context (Optional)</span>
            {clinicalContext.trim() && (
              <span className="text-xs text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/30 px-1.5 py-0.5 rounded">
                {contextCharCount.toLocaleString()} chars
              </span>
            )}
          </div>
          {showContext ? (
            <ChevronDown className="w-4 h-4 text-muted" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted" />
          )}
        </button>
        {showContext && (
          <div className="p-3 space-y-2">
            <p className="text-xs text-muted">
              Paste clinical guidelines, diagnostic criteria, or reference text to improve accuracy.
              The LLM will use these definitions for correct thresholds.
            </p>
            <textarea
              value={clinicalContext}
              onChange={(e) => setClinicalContext(e.target.value)}
              placeholder={`Example:
KDIGO AKI Criteria:
- Stage 1: Serum creatinine increase ≥0.3 mg/dL within 48h OR ≥1.5x baseline within 7 days
- Stage 2: Serum creatinine ≥2.0x baseline
- Stage 3: Serum creatinine ≥3.0x baseline OR ≥4.0 mg/dL OR initiation of RRT

Leukopenia Definition:
- WBC < 4.0 x10^9/L (or < 4000/µL)`}
              className="w-full h-32 px-3 py-2 bg-surface border border-border rounded text-foreground placeholder-muted focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm font-mono"
              disabled={isGenerating}
            />
            {contextWarning && (
              <p className="text-xs text-yellow-600 dark:text-yellow-400 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                Large context may slow generation. Consider summarizing key criteria only.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Generate Button & Status */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleGenerate}
          disabled={!canGenerate}
          className={`
            flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-colors
            ${canGenerate
              ? 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer'
              : 'bg-surface-hover text-muted cursor-not-allowed'
            }
          `}
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              {PHASE_MESSAGES[phase]}
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Generate Scenario
            </>
          )}
        </button>

        {/* Status Indicator */}
        {isGenerating && (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted">{formatTime(elapsedTime)}</span>
            <span className="text-muted">|</span>
            <span className="text-blue-600 dark:text-blue-400">{phaseDetail}</span>
          </div>
        )}
        {!isGenerating && phase === 'done' && (
          <span className="text-sm text-green-600 dark:text-green-400">{phaseDetail}</span>
        )}
        {!isGenerating && phase === 'error' && (
          <span className="text-sm text-red-600 dark:text-red-400">{phaseDetail}</span>
        )}
      </div>

      {/* Generated Output */}
      {generatedYaml && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-foreground">Generated PSDL</span>
              {attempts > 1 && (
                <span className="text-xs text-muted bg-surface-hover px-2 py-0.5 rounded">
                  {attempts} attempts
                </span>
              )}
              {elapsedTime > 0 && (
                <span className="text-xs text-muted">
                  in {formatTime(elapsedTime)}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              {isValid ? (
                <span className="flex items-center gap-1 text-green-600 dark:text-green-400 text-sm">
                  <CheckCircle className="w-4 h-4" />
                  Valid
                </span>
              ) : (
                <span className="flex items-center gap-1 text-yellow-600 dark:text-yellow-400 text-sm">
                  <AlertCircle className="w-4 h-4" />
                  {errors.length} issue{errors.length !== 1 ? 's' : ''}
                </span>
              )}
              <button
                onClick={handleUseThis}
                className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded text-sm font-medium transition-colors"
              >
                Use This
              </button>
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="px-3 py-1.5 bg-surface-hover hover:bg-border text-foreground rounded text-sm font-medium transition-colors disabled:opacity-50"
              >
                Retry
              </button>
            </div>
          </div>

          <pre className="p-4 bg-surface border border-border rounded-lg text-sm text-foreground overflow-auto max-h-72 font-mono">
            {generatedYaml}
          </pre>

          {/* Validation Issues */}
          {errors.length > 0 && (
            <div className="bg-red-100 dark:bg-red-900/20 border border-red-300 dark:border-red-800/50 rounded-lg p-3">
              <h4 className="text-sm font-semibold text-red-700 dark:text-red-400 mb-1">Errors</h4>
              <ul className="text-sm text-red-600 dark:text-red-300/80 space-y-1">
                {errors.map((e, i) => (
                  <li key={i}>• {e}</li>
                ))}
              </ul>
            </div>
          )}

          {warnings.length > 0 && (
            <div className="bg-yellow-100 dark:bg-yellow-900/20 border border-yellow-300 dark:border-yellow-800/50 rounded-lg p-3">
              <h4 className="text-sm font-semibold text-yellow-700 dark:text-yellow-400 mb-1">Warnings</h4>
              <ul className="text-sm text-yellow-600 dark:text-yellow-300/80 space-y-1">
                {warnings.map((w, i) => (
                  <li key={i}>• {w}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Error Display (generation errors) */}
      {!generatedYaml && !isGenerating && errors.length > 0 && (
        <div className="bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg p-3 text-sm text-red-700 dark:text-red-400">
          {errors.map((e, i) => (
            <div key={i}>• {e}</div>
          ))}
        </div>
      )}

      {/* Info Box */}
      <div className="bg-blue-100 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-300 dark:border-blue-800/50 text-sm">
        <h4 className="font-semibold text-blue-700 dark:text-blue-300 mb-1">How it works</h4>
        <p className="text-blue-600 dark:text-blue-200/80">
          Describe what clinical condition you want to detect. Choose OpenAI (fast, accurate) or
          Ollama (local, private). Optionally paste clinical guidelines for accurate thresholds.
          The AI generates PSDL and auto-corrects validation errors.
        </p>
      </div>

      {/* Example Prompts */}
      <div className="space-y-2">
        <h4 className="text-sm font-medium text-muted">Example prompts:</h4>
        <div className="flex flex-wrap gap-2">
          {[
            'Detect AKI using creatinine rise over 48 hours',
            'Monitor for sepsis using SIRS criteria',
            'Alert on critical potassium levels',
            'Track blood pressure trends for hypertension',
          ].map((example) => (
            <button
              key={example}
              onClick={() => setPrompt(example)}
              disabled={!status?.available || isGenerating}
              className="px-2 py-1 text-xs bg-surface-hover hover:bg-border text-foreground rounded border border-border transition-colors disabled:opacity-50"
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
