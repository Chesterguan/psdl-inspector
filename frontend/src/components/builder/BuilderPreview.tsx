'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import type { BuilderState, LogicRule, Signal } from './PSDLBuilder';
import { METRICS, OPERATORS } from './PSDLBuilder';

interface BuilderPreviewProps {
  state: BuilderState;
  onValidationChange?: (isValid: boolean) => void;
  onContinue?: () => void;
  isValidating?: boolean;
}

// Helper to get signal ID from signal
function getSignalId(signal: Signal): string {
  return signal.concept_name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/_+$/, '');
}

// Helper to get trend ID for a rule
function getTrendId(rule: LogicRule): string {
  if (!rule.signal) return '';
  const signalId = getSignalId(rule.signal);
  const metric = METRICS[rule.metric]?.expr || rule.metric;
  // All metrics need a trend - even 'current' uses last()
  if (rule.metric === 'current') return `${signalId}_current`;
  return `${signalId}_${metric}_${rule.window.value}${rule.window.unit}`;
}

export default function BuilderPreview({ state, onValidationChange, onContinue, isValidating }: BuilderPreviewProps) {
  const [activeTab, setActiveTab] = useState<'summary' | 'yaml'>('summary');
  const [validationStatus, setValidationStatus] = useState<'pending' | 'valid' | 'invalid'>('pending');
  const [validationMessage, setValidationMessage] = useState('Awaiting input');

  // Generate YAML
  const yaml = useMemo(() => generateYAML(state), [state]);

  // Stats
  const signalCount = useMemo(() => {
    const signals = new Set<number>();
    state.rules.forEach(r => {
      if (r.signal) signals.add(r.signal.concept_id);
      if (r.secondSignal) signals.add(r.secondSignal.concept_id);
    });
    return signals.size;
  }, [state.rules]);

  const ruleCount = state.rules.filter(r => r.signal || (r.useCustomExpression && r.customExpression)).length;

  // Validation
  useEffect(() => {
    if (!state.scenario.name) {
      setValidationStatus('pending');
      setValidationMessage('Enter scenario name');
      onValidationChange?.(false);
      return;
    }

    if (state.rules.filter(r => r.signal || r.useCustomExpression).length === 0) {
      setValidationStatus('pending');
      setValidationMessage('Add at least one logic rule');
      onValidationChange?.(false);
      return;
    }

    // Check if all non-composite rules have signals
    const incompleteRules = state.rules.filter(r => !r.useCustomExpression && !r.signal);
    if (incompleteRules.length > 0) {
      setValidationStatus('invalid');
      setValidationMessage(`${incompleteRules.length} rule(s) missing signal`);
      onValidationChange?.(false);
      return;
    }

    // Check if composite rules have valid expressions
    const invalidComposites = state.rules.filter(r => r.useCustomExpression && !r.customExpression);
    if (invalidComposites.length > 0) {
      setValidationStatus('invalid');
      setValidationMessage(`${invalidComposites.length} composite rule(s) missing expression`);
      onValidationChange?.(false);
      return;
    }

    setValidationStatus('valid');
    setValidationMessage('Valid PSDL scenario');
    onValidationChange?.(true);
  }, [state, onValidationChange]);

  // Copy YAML
  const copyYAML = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(yaml);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [yaml]);


  // Check if sections are filled
  const hasPopulation = state.population.include.conditions.length > 0 ||
    state.population.include.medications.length > 0 ||
    state.population.demographics.ageMin !== 18 ||
    state.population.demographics.ageMax !== 99 ||
    state.population.demographics.sex !== 'any';

  const hasAudit = state.audit.intent.length > 0 || state.audit.rationale.length > 0;

  const hasOutputs = state.outputs.decisions.length > 0 || state.outputs.features.length > 0;

  // Render summary
  const renderSummary = () => {
    const scenarioContent = state.scenario.name
      ? <><span className="px-1.5 py-0.5 bg-accent/10 rounded font-mono text-xs text-accent">{state.scenario.name}</span> <span className="text-muted text-xs">v{state.scenario.version}</span></>
      : <span className="text-muted italic">Enter scenario identifier...</span>;

    const populationContent = () => {
      const parts: string[] = [];

      if (state.population.include.conditions.length > 0) {
        parts.push(`${state.population.include.conditions.length} condition(s)`);
      }
      if (state.population.include.medications.length > 0) {
        parts.push(`${state.population.include.medications.length} medication(s)`);
      }
      if (state.population.demographics.ageMin !== 18 || state.population.demographics.ageMax !== 99) {
        parts.push(`age ${state.population.demographics.ageMin}-${state.population.demographics.ageMax}`);
      }
      if (state.population.demographics.sex !== 'any') {
        parts.push(state.population.demographics.sex);
      }

      if (parts.length === 0) {
        return <span className="text-muted italic">All adult patients (default)</span>;
      }

      return <span className="text-foreground-secondary">{parts.join(', ')}</span>;
    };

    const logicContent = () => {
      const validRules = state.rules.filter(r => r.signal || (r.useCustomExpression && r.customExpression));

      if (validRules.length === 0) {
        return <span className="text-muted italic">Define logic rules...</span>;
      }

      return (
        <div className="space-y-1.5">
          {validRules.map((rule) => {
            let description: string;

            if (rule.useCustomExpression) {
              description = rule.customExpression;
            } else if (rule.signal) {
              const signalName = rule.signal.concept_name || 'Signal';
              const metricLabel = METRICS[rule.metric]?.label || rule.metric;
              const opLabel = OPERATORS.find(o => o.value === rule.operator)?.label || rule.operator;
              const unit = rule.metric === 'percent_change' ? '%' : (rule.signal.typical_units?.[0]?.code || '');

              description = `${signalName} ${metricLabel}`;
              if (METRICS[rule.metric]?.needsWindow) {
                description += ` ${rule.window.value}${rule.window.unit}`;
              }
              description += ` ${opLabel} ${rule.value}${unit}`;
            } else {
              description = 'Incomplete rule';
            }

            return (
              <div key={rule.id} className="px-2 py-1.5 bg-background-tertiary/50 rounded text-xs border-l-2 border-accent-warning">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="font-mono font-semibold text-accent-cyan">{rule.name}</span>
                  <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${
                    rule.severity === 'low' ? 'bg-accent-success/10 text-accent-success' :
                    rule.severity === 'medium' ? 'bg-accent-warning/10 text-accent-warning' :
                    'bg-accent-danger/10 text-accent-danger'
                  }`}>
                    {rule.severity}
                  </span>
                </div>
                <div className="text-foreground-secondary">{description}</div>
              </div>
            );
          })}
        </div>
      );
    };

    const auditContent = () => {
      if (!hasAudit) {
        return <span className="text-muted italic">Enter audit info...</span>;
      }
      return (
        <div className="text-foreground-secondary text-xs space-y-1">
          {state.audit.intent && <div>Intent: <span className="text-foreground">{state.audit.intent.substring(0, 50)}...</span></div>}
          {state.audit.rationale && <div>Rationale: <span className="text-foreground">{state.audit.rationale.substring(0, 50)}...</span></div>}
          {state.audit.provenance && <div>Provenance: <span className="text-foreground">{state.audit.provenance}</span></div>}
        </div>
      );
    };

    const outputsContent = () => {
      if (!hasOutputs) {
        return <span className="text-muted italic">Define outputs...</span>;
      }
      return (
        <div className="text-foreground-secondary text-xs space-y-1">
          {state.outputs.decisions.length > 0 && (
            <div>{state.outputs.decisions.length} decision(s): {state.outputs.decisions.map(d => d.name).join(', ')}</div>
          )}
          {state.outputs.features.length > 0 && (
            <div>{state.outputs.features.length} feature(s): {state.outputs.features.map(f => f.name).join(', ')}</div>
          )}
        </div>
      );
    };

    return (
      <div className="space-y-2">
        {/* 01 Scenario Card */}
        <div className={`bg-background rounded overflow-hidden ${state.scenario.name ? 'ring-1 ring-accent/20' : ''}`}>
          <div className="flex items-center gap-1.5 px-2.5 py-2 bg-background-tertiary/30">
            <span className={`w-5 h-5 flex items-center justify-center rounded text-xs font-bold font-mono ${state.scenario.name ? 'bg-accent-cyan/20 text-accent-cyan' : 'bg-background-tertiary text-muted'}`}>01</span>
            <span className="text-xs font-semibold text-foreground-secondary">Scenario</span>
          </div>
          <div className="px-2.5 py-2 text-sm">
            {scenarioContent}
          </div>
        </div>

        {/* 02 Population Card */}
        <div className={`bg-background rounded overflow-hidden ${hasPopulation ? 'ring-1 ring-accent/20' : ''}`}>
          <div className="flex items-center gap-1.5 px-2.5 py-2 bg-background-tertiary/30">
            <span className={`w-5 h-5 flex items-center justify-center rounded text-xs font-bold font-mono ${hasPopulation ? 'bg-accent-cyan/20 text-accent-cyan' : 'bg-background-tertiary text-muted'}`}>02</span>
            <span className="text-xs font-semibold text-foreground-secondary">Population</span>
          </div>
          <div className="px-2.5 py-2 text-sm">
            {populationContent()}
          </div>
        </div>

        {/* 03 Logic Card */}
        <div className={`bg-background rounded overflow-hidden ${ruleCount > 0 ? 'ring-1 ring-accent/20' : ''}`}>
          <div className="flex items-center gap-1.5 px-2.5 py-2 bg-background-tertiary/30">
            <span className={`w-5 h-5 flex items-center justify-center rounded text-xs font-bold font-mono ${ruleCount > 0 ? 'bg-accent-cyan/20 text-accent-cyan' : 'bg-background-tertiary text-muted'}`}>03</span>
            <span className="text-xs font-semibold text-foreground-secondary">Logic Rules</span>
          </div>
          <div className="px-2.5 py-2 text-sm">
            {logicContent()}
          </div>
        </div>

        {/* 04 Audit Card */}
        <div className={`bg-background rounded overflow-hidden ${hasAudit ? 'ring-1 ring-accent/20' : ''}`}>
          <div className="flex items-center gap-1.5 px-2.5 py-2 bg-background-tertiary/30">
            <span className={`w-5 h-5 flex items-center justify-center rounded text-xs font-bold font-mono ${hasAudit ? 'bg-accent-cyan/20 text-accent-cyan' : 'bg-background-tertiary text-muted'}`}>04</span>
            <span className="text-xs font-semibold text-foreground-secondary">Audit</span>
          </div>
          <div className="px-2.5 py-2 text-sm">
            {auditContent()}
          </div>
        </div>

        {/* 05 Outputs Card */}
        <div className={`bg-background rounded overflow-hidden ${hasOutputs ? 'ring-1 ring-accent/20' : ''}`}>
          <div className="flex items-center gap-1.5 px-2.5 py-2 bg-background-tertiary/30">
            <span className={`w-5 h-5 flex items-center justify-center rounded text-xs font-bold font-mono ${hasOutputs ? 'bg-accent-cyan/20 text-accent-cyan' : 'bg-background-tertiary text-muted'}`}>05</span>
            <span className="text-xs font-semibold text-foreground-secondary">Outputs</span>
          </div>
          <div className="px-2.5 py-2 text-sm">
            {outputsContent()}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="preview-panel bg-background-secondary rounded-lg sticky top-20 max-h-[calc(100vh-120px)] flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between border-b border-border/30">
        <span className="text-sm font-semibold text-foreground uppercase tracking-wide">Preview</span>
        <div className="flex gap-0.5 p-0.5 bg-background rounded">
          <button
            className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
              activeTab === 'summary' ? 'bg-accent text-white' : 'text-foreground-secondary hover:text-foreground'
            }`}
            onClick={() => setActiveTab('summary')}
          >
            Summary
          </button>
          <button
            className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
              activeTab === 'yaml' ? 'bg-accent text-white' : 'text-foreground-secondary hover:text-foreground'
            }`}
            onClick={() => setActiveTab('yaml')}
          >
            YAML
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {/* Validation Status */}
        <div className={`px-3 py-2.5 mb-3 rounded text-sm font-medium ${
          validationStatus === 'valid'
            ? 'bg-accent-success/10 text-accent-success'
            : validationStatus === 'invalid'
            ? 'bg-accent-danger/10 text-accent-danger'
            : 'bg-accent-warning/10 text-accent-warning'
        }`}>
          {validationMessage}
        </div>

        {activeTab === 'summary' && renderSummary()}

        {activeTab === 'yaml' && (
          <pre className="bg-background rounded p-3 font-mono text-xs leading-relaxed overflow-x-auto whitespace-pre-wrap text-foreground-secondary max-h-[350px] overflow-y-auto">
            {yaml}
          </pre>
        )}
      </div>

      {/* Stats Footer */}
      <div className="flex justify-center gap-8 py-3 px-4 border-t border-border/30">
        <div className="text-center">
          <span className="block font-mono text-xl font-semibold text-accent-cyan">{signalCount}</span>
          <span className="text-xs uppercase tracking-wider text-foreground-secondary">Signals</span>
        </div>
        <div className="text-center">
          <span className="block font-mono text-xl font-semibold text-accent-cyan">{ruleCount}</span>
          <span className="text-xs uppercase tracking-wider text-foreground-secondary">Rules</span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-2 p-3">
        <div className="flex gap-2">
          <button
            className="flex-1 py-2.5 px-3 bg-background hover:bg-background-tertiary text-foreground text-sm font-medium rounded-md transition-colors"
            onClick={copyYAML}
          >
            Copy YAML
          </button>
          <button
            className="flex-1 py-2.5 px-3 bg-accent hover:bg-accent-hover text-white text-sm font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={onContinue}
            disabled={validationStatus !== 'valid' || !onContinue || isValidating}
            title={validationStatus !== 'valid' ? validationMessage : ''}
          >
            {isValidating ? 'Validating...' : 'Continue →'}
          </button>
        </div>
        {validationStatus !== 'valid' && (
          <p className="text-xs text-center text-muted">
            {validationMessage}
          </p>
        )}
      </div>
    </div>
  );
}

// YAML Generation - Updated for full PSDL spec
function generateYAML(state: BuilderState): string {
  const lines: string[] = [];

  // Scenario
  lines.push(`scenario: ${state.scenario.name || 'untitled'}`);
  lines.push(`version: "${state.scenario.version}"`);
  if (state.scenario.description) {
    lines.push(`description: "${state.scenario.description}"`);
  }
  lines.push('');

  // Population
  if (state.population.include.conditions.length > 0 ||
      state.population.include.medications.length > 0 ||
      state.population.exclude.conditions.length > 0 ||
      state.population.exclude.medications.length > 0 ||
      state.population.demographics.ageMin !== 18 ||
      state.population.demographics.ageMax !== 99 ||
      state.population.demographics.sex !== 'any') {
    lines.push('population:');

    if (state.population.include.conditions.length > 0 || state.population.include.medications.length > 0) {
      lines.push('  include:');
      if (state.population.include.conditions.length > 0) {
        lines.push('    conditions:');
        state.population.include.conditions.forEach(c => {
          lines.push(`      - code: "${c.concept_code}"`);
          lines.push(`        system: ${c.vocabulary_id}`);
        });
      }
      if (state.population.include.medications.length > 0) {
        lines.push('    medications:');
        state.population.include.medications.forEach(m => {
          lines.push(`      - code: "${m.concept_code}"`);
          lines.push(`        system: ${m.vocabulary_id}`);
        });
      }
    }

    if (state.population.exclude.conditions.length > 0 || state.population.exclude.medications.length > 0) {
      lines.push('  exclude:');
      if (state.population.exclude.conditions.length > 0) {
        lines.push('    conditions:');
        state.population.exclude.conditions.forEach(c => {
          lines.push(`      - code: "${c.concept_code}"`);
          lines.push(`        system: ${c.vocabulary_id}`);
        });
      }
      if (state.population.exclude.medications.length > 0) {
        lines.push('    medications:');
        state.population.exclude.medications.forEach(m => {
          lines.push(`      - code: "${m.concept_code}"`);
          lines.push(`        system: ${m.vocabulary_id}`);
        });
      }
    }

    if (state.population.demographics.ageMin !== 18 ||
        state.population.demographics.ageMax !== 99 ||
        state.population.demographics.sex !== 'any') {
      lines.push('  demographics:');
      lines.push(`    age_min: ${state.population.demographics.ageMin}`);
      lines.push(`    age_max: ${state.population.demographics.ageMax}`);
      if (state.population.demographics.sex !== 'any') {
        lines.push(`    sex: ${state.population.demographics.sex}`);
      }
    }
    lines.push('');
  }

  // Collect all signals used
  const usedSignals = new Map<number, Signal>();
  state.rules.forEach(r => {
    if (r.signal) usedSignals.set(r.signal.concept_id, r.signal);
    if (r.secondSignal) usedSignals.set(r.secondSignal.concept_id, r.secondSignal);
  });

  // Signals section
  if (usedSignals.size > 0) {
    lines.push('signals:');
    usedSignals.forEach((signal) => {
      const id = getSignalId(signal);
      lines.push(`  ${id}:`);
      // psdl-lang uses 'ref' for semantic reference (e.g., LOINC code or concept name)
      const ref = signal.concept_code || signal.concept_name.toLowerCase().replace(/[^a-z0-9]+/g, '_');
      lines.push(`    ref: ${ref}`);
      if (signal.typical_units?.[0]) {
        lines.push(`    unit: ${signal.typical_units[0].code}`);
      }
    });
    lines.push('');
  }

  // Trends section - ALL rules need trends (including 'current' which uses last())
  const trendsNeeded = state.rules.filter(r => r.signal && !r.useCustomExpression);
  if (trendsNeeded.length > 0) {
    lines.push('trends:');
    trendsNeeded.forEach((r) => {
      if (!r.signal) return;
      const signalId = getSignalId(r.signal);
      const trendId = getTrendId(r);
      const metric = METRICS[r.metric]?.expr || r.metric;

      lines.push(`  ${trendId}:`);
      // 'current' uses last(), others use metric(signal, window)
      if (r.metric === 'current') {
        lines.push(`    expr: last(${signalId})`);
      } else {
        lines.push(`    expr: ${metric}(${signalId}, ${r.window.value}${r.window.unit})`);
      }
      if (r.description) {
        lines.push(`    description: "${r.description}"`);
      }
    });
    lines.push('');
  }

  // Logic section - multiple named rules
  const validRules = state.rules.filter(r => r.signal || (r.useCustomExpression && r.customExpression));
  if (validRules.length > 0) {
    lines.push('logic:');
    validRules.forEach((r) => {
      lines.push(`  ${r.name}:`);

      // Build the 'when' expression
      let whenExpr: string;
      if (r.useCustomExpression && r.customExpression) {
        whenExpr = r.customExpression;
      } else if (r.signal) {
        // Always reference trends (not raw signals) - psdl-lang requires this
        const trendRef = getTrendId(r);
        const op = OPERATORS.find(o => o.value === r.operator)?.symbol || '>=';
        whenExpr = `${trendRef} ${op} ${r.value}`;
      } else {
        whenExpr = 'true';
      }

      lines.push(`    when: ${whenExpr}`);
      lines.push(`    severity: ${r.severity}`);
      if (r.description) {
        lines.push(`    description: "${r.description}"`);
      }
      if (r.recommendation) {
        lines.push(`    recommendation: "${r.recommendation}"`);
      }
    });
    lines.push('');
  }

  // Outputs section - psdl-lang requires structured format
  if (state.outputs.decisions.length > 0 || state.outputs.features.length > 0 || state.outputs.includeTimestamp) {
    lines.push('outputs:');
    if (state.outputs.decisions.length > 0) {
      lines.push('  decision:');
      state.outputs.decisions.forEach(d => {
        lines.push(`    ${d.name}:`);
        lines.push(`      type: boolean`);
        lines.push(`      from: logic.${d.fromRule}`);
      });
    }
    if (state.outputs.features.length > 0) {
      lines.push('  features:');
      state.outputs.features.forEach(f => {
        lines.push(`    ${f.name}:`);
        lines.push(`      type: float`);
        lines.push(`      from: trends.${f.fromTrend}`);
      });
    }
    if (state.outputs.includeTimestamp) {
      lines.push('  evidence:');
      lines.push('    timestamp:');
      lines.push('      type: datetime');
      lines.push('      expr: evaluation_time()');
    }
    lines.push('');
  }

  // Audit section - updated for PSDL spec
  if (state.audit.intent || state.audit.rationale || state.audit.provenance) {
    lines.push('audit:');
    if (state.audit.intent) {
      lines.push(`  intent: "${state.audit.intent}"`);
    }
    if (state.audit.rationale) {
      lines.push(`  rationale: "${state.audit.rationale}"`);
    }
    if (state.audit.provenance) {
      lines.push(`  provenance: "${state.audit.provenance}"`);
    }
  }

  return lines.join('\n');
}
