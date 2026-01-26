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
  onContinue?: (yaml: string) => void;
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

export default function GenerationPanel({ onUseGenerated, onContinue }: GenerationPanelProps) {
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

      if (data.default_provider) {
        setProvider(data.default_provider as Provider);
      }

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
  }, []);

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
    <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_340px] xl:grid-cols-[minmax(0,1fr)_400px] gap-6">
      {/* Left: Generation Form */}
      <div className="space-y-4">
        {/* Section 1: Provider */}
        <div className="section-panel bg-background-secondary rounded-lg overflow-hidden">
          <div className="section-header flex items-center justify-between px-4 py-3 bg-background-tertiary">
            <div className="flex items-center gap-3">
              <span className="section-number w-7 h-7 flex items-center justify-center bg-accent-cyan/20 rounded font-mono text-sm font-bold text-accent-cyan">01</span>
              <span className="section-title text-sm font-semibold text-foreground">Provider Selection</span>
            </div>
            <button
              onClick={checkStatus}
              className="p-1.5 hover:bg-background rounded transition-colors"
              title="Refresh status"
              disabled={isGenerating}
            >
              <RefreshCw className="w-4 h-4 text-foreground-secondary" />
            </button>
          </div>
          <div className="section-body px-4 py-4">
            <div className="flex items-center gap-3 flex-wrap">
              {/* OpenAI Button */}
              <button
                onClick={() => setProvider('openai')}
                disabled={isGenerating || !status?.openai.available}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  provider === 'openai'
                    ? 'bg-accent text-white'
                    : 'bg-background hover:bg-background-tertiary text-foreground'
                } ${!status?.openai.available ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <Cloud className="w-4 h-4" />
                OpenAI
                {status?.openai.available && status.openai.model && (
                  <span className="text-xs opacity-70">{status.openai.model}</span>
                )}
              </button>

              {/* Ollama Button */}
              <button
                onClick={() => setProvider('ollama')}
                disabled={isGenerating || !status?.ollama.available}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  provider === 'ollama'
                    ? 'bg-accent-success text-white'
                    : 'bg-background hover:bg-background-tertiary text-foreground'
                } ${!status?.ollama.available ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <Server className="w-4 h-4" />
                Ollama
              </button>

              {/* Ollama Model Selector */}
              {provider === 'ollama' && status?.ollama.available && status.ollama.models && status.ollama.models.length > 0 && (
                <select
                  value={selectedOllamaModel || ''}
                  onChange={(e) => setSelectedOllamaModel(e.target.value)}
                  className="px-3 py-2.5 bg-background rounded-md text-foreground text-sm cursor-pointer outline-none focus:ring-2 focus:ring-accent/30"
                  disabled={isGenerating}
                >
                  {status.ollama.models.map((model) => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                </select>
              )}

              {/* Status Indicators */}
              <div className="ml-auto flex items-center gap-3 text-xs">
                {status?.openai.available ? (
                  <span className="text-accent-success flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5" /> OpenAI
                  </span>
                ) : (
                  <span className="text-foreground-secondary flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" /> OpenAI
                  </span>
                )}
                {status?.ollama.available ? (
                  <span className="text-accent-success flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5" /> Ollama
                  </span>
                ) : (
                  <span className="text-foreground-secondary flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" /> Ollama
                  </span>
                )}
              </div>
            </div>

            {/* No Provider Warning */}
            {status && !status.available && (
              <div className="mt-4 p-4 bg-accent-warning/10 rounded-lg border border-accent-warning/20">
                <h4 className="font-semibold text-accent-warning text-sm mb-2">No LLM Provider Available</h4>
                <p className="text-foreground-secondary text-sm mb-3">Configure at least one provider:</p>
                <pre className="bg-background p-3 rounded text-xs text-foreground font-mono overflow-x-auto">
{`# Option 1: OpenAI (recommended)
export OPENAI_API_KEY="sk-..."

# Option 2: Local Ollama
brew install ollama
ollama serve
ollama pull mistral-small`}
                </pre>
              </div>
            )}
          </div>
        </div>

        {/* Section 2: Prompt */}
        <div className="section-panel bg-background-secondary rounded-lg overflow-hidden">
          <div className="section-header flex items-center gap-3 px-4 py-3 bg-background-tertiary">
            <span className="section-number w-7 h-7 flex items-center justify-center bg-accent-cyan/20 rounded font-mono text-sm font-bold text-accent-cyan">02</span>
            <span className="section-title text-sm font-semibold text-foreground">Scenario Description</span>
          </div>
          <div className="section-body px-4 py-4">
            <label className="form-label block text-sm font-semibold text-foreground-secondary mb-2">
              Describe your clinical scenario
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Example: Detect early sepsis in ICU patients using temperature, heart rate, respiratory rate, and white blood cell count. Alert when multiple SIRS criteria are met."
              className="w-full h-32 px-3 py-3 bg-background rounded-md text-foreground text-sm placeholder:text-muted/50 focus:ring-2 focus:ring-accent/30 outline-none resize-none transition-all"
              disabled={!status?.available || isGenerating}
            />

            {/* Example Prompts */}
            <div className="mt-3">
              <span className="text-xs font-semibold text-foreground-secondary">Quick examples:</span>
              <div className="flex flex-wrap gap-2 mt-2">
                {[
                  'Detect AKI using creatinine rise over 48 hours',
                  'Monitor for sepsis using SIRS criteria',
                  'Alert on critical potassium levels',
                ].map((example) => (
                  <button
                    key={example}
                    onClick={() => setPrompt(example)}
                    disabled={!status?.available || isGenerating}
                    className="px-2.5 py-1.5 text-xs bg-background hover:bg-background-tertiary text-foreground-secondary hover:text-foreground rounded-md transition-colors disabled:opacity-50"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: Clinical Context (Collapsible) */}
        <div className="section-panel bg-background-secondary rounded-lg overflow-hidden">
          <button
            onClick={() => setShowContext(!showContext)}
            className="w-full section-header flex items-center justify-between px-4 py-3 bg-background-tertiary hover:bg-background-tertiary/80 transition-colors"
            disabled={isGenerating}
          >
            <div className="flex items-center gap-3">
              <span className="section-number w-7 h-7 flex items-center justify-center bg-accent-cyan/20 rounded font-mono text-sm font-bold text-accent-cyan">03</span>
              <BookOpen className="w-4 h-4 text-foreground-secondary" />
              <span className="section-title text-sm font-semibold text-foreground">Clinical Context</span>
              <span className="text-xs text-foreground-secondary">(Optional)</span>
              {clinicalContext.trim() && (
                <span className="text-xs text-accent bg-accent/10 px-2 py-0.5 rounded">
                  {contextCharCount.toLocaleString()} chars
                </span>
              )}
            </div>
            {showContext ? (
              <ChevronDown className="w-4 h-4 text-foreground-secondary" />
            ) : (
              <ChevronRight className="w-4 h-4 text-foreground-secondary" />
            )}
          </button>
          {showContext && (
            <div className="section-body px-4 pb-4">
              <p className="text-xs text-foreground-secondary mb-3">
                Paste clinical guidelines, diagnostic criteria, or reference text to improve accuracy.
              </p>
              <textarea
                value={clinicalContext}
                onChange={(e) => setClinicalContext(e.target.value)}
                placeholder={`Example:
KDIGO AKI Criteria:
- Stage 1: Serum creatinine increase >= 0.3 mg/dL within 48h
- Stage 2: Serum creatinine >= 2.0x baseline
- Stage 3: Serum creatinine >= 3.0x baseline`}
                className="w-full h-36 px-3 py-3 bg-background rounded-md text-foreground text-sm font-mono placeholder:text-muted/50 focus:ring-2 focus:ring-accent/30 outline-none resize-none transition-all"
                disabled={isGenerating}
              />
              {contextWarning && (
                <p className="mt-2 text-xs text-accent-warning flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  Large context may slow generation. Consider summarizing key criteria only.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Generate Button */}
        <div className="flex items-center gap-4">
          <button
            onClick={handleGenerate}
            disabled={!canGenerate}
            className={`flex items-center gap-2 px-5 py-3 rounded-lg font-medium text-sm transition-colors ${
              canGenerate
                ? 'bg-accent-purple hover:bg-accent-purple/90 text-white cursor-pointer'
                : 'bg-background-tertiary text-muted cursor-not-allowed'
            }`}
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

          {/* Status */}
          {isGenerating && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-foreground-secondary font-mono">{formatTime(elapsedTime)}</span>
              <span className="text-foreground-secondary">|</span>
              <span className="text-accent">{phaseDetail}</span>
            </div>
          )}
          {!isGenerating && phase === 'done' && (
            <span className="text-sm text-accent-success">{phaseDetail}</span>
          )}
          {!isGenerating && phase === 'error' && (
            <span className="text-sm text-accent-danger">{phaseDetail}</span>
          )}
        </div>
      </div>

      {/* Right: Preview Panel */}
      <div className="preview-panel bg-background-secondary rounded-lg sticky top-20 max-h-[calc(100vh-120px)] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-4 py-3 flex items-center justify-between border-b border-border/30">
          <span className="text-xs font-semibold text-foreground uppercase tracking-wide">Generated Output</span>
          {generatedYaml && (
            <div className="flex items-center gap-2">
              {isValid ? (
                <span className="flex items-center gap-1 text-accent-success text-xs font-medium">
                  <CheckCircle className="w-3.5 h-3.5" /> Valid
                </span>
              ) : (
                <span className="flex items-center gap-1 text-accent-warning text-xs font-medium">
                  <AlertCircle className="w-3.5 h-3.5" /> {errors.length} issue{errors.length !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {!generatedYaml && !isGenerating && (
            <div className="h-full flex flex-col items-center justify-center text-center py-12">
              <Sparkles className="w-10 h-10 text-accent-purple/30 mb-4" />
              <p className="text-sm text-foreground-secondary">Describe a scenario and click Generate</p>
              <p className="text-xs text-muted mt-1">The AI will create PSDL for you</p>
            </div>
          )}

          {isGenerating && (
            <div className="h-full flex flex-col items-center justify-center text-center py-12">
              <Loader2 className="w-10 h-10 text-accent-purple animate-spin mb-4" />
              <p className="text-sm text-foreground">{PHASE_MESSAGES[phase]}</p>
              <p className="text-xs text-foreground-secondary mt-1">{phaseDetail}</p>
            </div>
          )}

          {generatedYaml && (
            <div className="space-y-4">
              {/* Meta info */}
              <div className="flex items-center gap-3 text-xs text-foreground-secondary">
                {attempts > 1 && (
                  <span className="bg-background px-2 py-1 rounded">{attempts} attempts</span>
                )}
                {elapsedTime > 0 && (
                  <span>Generated in {formatTime(elapsedTime)}</span>
                )}
              </div>

              {/* YAML Preview */}
              <pre className="bg-background rounded-lg p-3 font-mono text-xs leading-relaxed overflow-x-auto whitespace-pre-wrap text-foreground-secondary max-h-[300px] overflow-y-auto">
                {generatedYaml}
              </pre>

              {/* Errors */}
              {errors.length > 0 && (
                <div className="p-3 bg-accent-danger/10 rounded-lg border border-accent-danger/20">
                  <h4 className="text-xs font-semibold text-accent-danger mb-2">Errors</h4>
                  <ul className="text-xs text-accent-danger space-y-1">
                    {errors.map((e, i) => (
                      <li key={i}>- {e}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Warnings */}
              {warnings.length > 0 && (
                <div className="p-3 bg-accent-warning/10 rounded-lg border border-accent-warning/20">
                  <h4 className="text-xs font-semibold text-accent-warning mb-2">Warnings</h4>
                  <ul className="text-xs text-accent-warning space-y-1">
                    {warnings.map((w, i) => (
                      <li key={i}>- {w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        {generatedYaml && (
          <div className="flex flex-col gap-2 p-3 border-t border-border/30">
            <div className="flex gap-2">
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="flex-1 py-2.5 px-3 bg-background hover:bg-background-tertiary text-foreground text-sm font-medium rounded-md transition-colors disabled:opacity-50"
              >
                Regenerate
              </button>
              <button
                onClick={handleUseThis}
                className="flex-1 py-2.5 px-3 bg-background hover:bg-background-tertiary text-foreground text-sm font-medium rounded-md transition-colors"
              >
                Edit in YAML
              </button>
            </div>
            {isValid && onContinue && (
              <button
                onClick={() => onContinue(generatedYaml)}
                className="w-full py-2.5 px-3 bg-accent hover:bg-accent-hover text-white text-sm font-medium rounded-md transition-colors"
              >
                Continue to Preview
              </button>
            )}
          </div>
        )}

        {/* Info */}
        <div className="px-4 pb-4">
          <div className="p-3 bg-accent/5 rounded-lg border border-accent/10">
            <p className="text-xs text-foreground-secondary">
              <span className="font-semibold text-accent">Tip:</span> Add clinical context for more accurate thresholds
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
