'use client';

import { useState, useCallback, useEffect } from 'react';
import ScenarioSection from './ScenarioSection';
import PopulationSection from './PopulationSection';
import LogicRulesSection from './LogicRulesSection';
import OutputsSection from './OutputsSection';
import BuilderPreview from './BuilderPreview';
import Tooltip, { GLOSSARY } from './Tooltip';

// Types
export interface Signal {
  concept_id: number;
  concept_name: string;
  concept_code: string;
  vocabulary_id: string;
  typical_units?: { code: string; name: string }[];
  _score?: number;
}

// Updated: LogicRule replaces Condition with full PSDL spec support
export interface LogicRule {
  id: number;
  name: string;  // User-defined rule name like 'aki_stage1'
  signal: Signal | null;
  metric: string;
  secondSignal: Signal | null;
  window: { value: number; unit: string };
  operator: string;
  value: number;
  severity: 'low' | 'medium' | 'high';
  description: string;
  recommendation: string;
  // For composite rules that reference other rules
  useCustomExpression: boolean;
  customExpression: string;  // e.g., "aki_stage1 AND bun_rising"
}

// Keep Condition as alias for backward compatibility
export type Condition = LogicRule;

export interface PopulationItem {
  concept_id: number;
  concept_name: string;
  concept_code: string;
  vocabulary_id: string;
}

export interface OutputDecision {
  name: string;
  fromRule: string;
}

export interface OutputFeature {
  name: string;
  fromTrend: string;
}

export interface BuilderState {
  scenario: {
    name: string;
    description: string;
    version: string;
  };
  population: {
    include: { conditions: PopulationItem[]; medications: PopulationItem[] };
    exclude: { conditions: PopulationItem[]; medications: PopulationItem[] };
    demographics: { ageMin: number; ageMax: number; sex: string };
  };
  // Updated: rules instead of conditions
  rules: LogicRule[];
  // Updated: audit with proper PSDL fields
  audit: {
    intent: string;
    rationale: string;
    provenance: string;
  };
  outputs: {
    decisions: OutputDecision[];
    features: OutputFeature[];
    includeTimestamp: boolean;
  };
}

// Keep conditions getter for backward compatibility
export function getConditions(state: BuilderState): LogicRule[] {
  return state.rules;
}

export const METRICS: Record<string, { label: string; expr: string; needsWindow: boolean; needsSecondSignal: boolean }> = {
  current: { label: 'current value', expr: '', needsWindow: false, needsSecondSignal: false },
  delta: { label: 'change over', expr: 'delta', needsWindow: true, needsSecondSignal: false },
  rate: { label: 'rate of change over', expr: 'rate', needsWindow: true, needsSecondSignal: false },
  percent_change: { label: '% change over', expr: 'percent_change', needsWindow: true, needsSecondSignal: false },
  min: { label: 'minimum over', expr: 'min', needsWindow: true, needsSecondSignal: false },
  max: { label: 'maximum over', expr: 'max', needsWindow: true, needsSecondSignal: false },
  avg: { label: 'average over', expr: 'avg', needsWindow: true, needsSecondSignal: false },
  slope: { label: 'slope over', expr: 'slope', needsWindow: true, needsSecondSignal: false },
  ratio: { label: 'divided by', expr: 'ratio', needsWindow: false, needsSecondSignal: true },
  difference: { label: 'minus', expr: 'difference', needsWindow: false, needsSecondSignal: true }
};

export const OPERATORS = [
  { value: 'gt', label: 'is above', symbol: '>' },
  { value: 'gte', label: 'is at or above', symbol: '>=' },
  { value: 'lt', label: 'is below', symbol: '<' },
  { value: 'lte', label: 'is at or below', symbol: '<=' },
  { value: 'eq', label: 'equals', symbol: '==' }
];

export const SEVERITIES = [
  { value: 'low', label: 'Low', color: 'accent-success' },
  { value: 'medium', label: 'Medium', color: 'accent-warning' },
  { value: 'high', label: 'High', color: 'accent-danger' }
];

const initialState: BuilderState = {
  scenario: { name: '', description: '', version: '1.0.0' },
  population: {
    include: { conditions: [], medications: [] },
    exclude: { conditions: [], medications: [] },
    demographics: { ageMin: 18, ageMax: 99, sex: 'any' }
  },
  rules: [],
  audit: { intent: '', rationale: '', provenance: '' },
  outputs: {
    decisions: [],
    features: [],
    includeTimestamp: true
  }
};

interface PSDLBuilderProps {
  onYamlChange: (yaml: string) => void;
  onValidationChange?: (isValid: boolean) => void;
  onContinue?: () => void;
  isValidating?: boolean;
}

export default function PSDLBuilder({ onYamlChange, onValidationChange, onContinue, isValidating }: PSDLBuilderProps) {
  const [state, setState] = useState<BuilderState>(initialState);
  const [ruleIdCounter, setRuleIdCounter] = useState(0);
  const [vocabVersion, setVocabVersion] = useState('Loading...');

  // Fetch vocabulary version on mount (optional feature - fails silently if unavailable)
  useEffect(() => {
    async function fetchVocab() {
      try {
        const resp = await fetch('http://localhost:8200/api/vocabulary/version');
        if (!resp.ok) {
          setVocabVersion('Not configured');
          return;
        }
        const data = await resp.json();
        setVocabVersion(`OMOP ${data.omop_cdm_version} // LOINC ${data.loinc_version}`);
      } catch {
        setVocabVersion('Not configured');
      }
    }
    fetchVocab();
  }, []);

  // Generate YAML whenever state changes
  useEffect(() => {
    const yaml = generateYAML(state);
    onYamlChange(yaml);
  }, [state, onYamlChange]);

  // Update scenario
  const updateScenario = useCallback((field: string, value: string) => {
    setState(prev => ({
      ...prev,
      scenario: { ...prev.scenario, [field]: value }
    }));
  }, []);

  // Update population
  const updatePopulation = useCallback((
    type: 'include' | 'exclude',
    category: 'conditions' | 'medications',
    items: PopulationItem[]
  ) => {
    setState(prev => ({
      ...prev,
      population: {
        ...prev.population,
        [type]: { ...prev.population[type], [category]: items }
      }
    }));
  }, []);

  const updateDemographics = useCallback((field: string, value: number | string) => {
    setState(prev => ({
      ...prev,
      population: {
        ...prev.population,
        demographics: { ...prev.population.demographics, [field]: value }
      }
    }));
  }, []);

  // Generate rule name from scenario name and index
  const generateRuleName = useCallback((index: number) => {
    const base = state.scenario.name || 'rule';
    const sanitized = base.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/_+$/, '');
    return `${sanitized}_${String(index + 1).padStart(2, '0')}`;
  }, [state.scenario.name]);

  // Add rule
  const addRule = useCallback(() => {
    const newId = ruleIdCounter + 1;
    setRuleIdCounter(newId);

    const newRule: LogicRule = {
      id: newId,
      name: generateRuleName(state.rules.length),
      signal: null,
      metric: 'current',
      secondSignal: null,
      window: { value: 48, unit: 'h' },
      operator: 'gte',
      value: 0,
      severity: 'medium',
      description: '',
      recommendation: '',
      useCustomExpression: false,
      customExpression: ''
    };

    setState(prev => ({
      ...prev,
      rules: [...prev.rules, newRule]
    }));
  }, [ruleIdCounter, generateRuleName, state.rules.length]);

  // Remove rule
  const removeRule = useCallback((id: number) => {
    setState(prev => ({
      ...prev,
      rules: prev.rules.filter(r => r.id !== id)
    }));
  }, []);

  // Update rule
  const updateRule = useCallback((id: number, field: string, value: unknown) => {
    setState(prev => ({
      ...prev,
      rules: prev.rules.map(r => {
        if (r.id !== id) return r;

        if (field.includes('.')) {
          const [parent, child] = field.split('.');
          return {
            ...r,
            [parent]: { ...(r[parent as keyof LogicRule] as Record<string, unknown>), [child]: value }
          };
        }

        const updated = { ...r, [field]: value };

        // Clear second signal if metric doesn't need it
        if (field === 'metric' && !METRICS[value as string].needsSecondSignal) {
          updated.secondSignal = null;
        }

        return updated;
      })
    }));
  }, []);

  // Update audit
  const updateAudit = useCallback((field: string, value: string) => {
    setState(prev => ({
      ...prev,
      audit: { ...prev.audit, [field]: value }
    }));
  }, []);

  // Update outputs
  const updateOutputs = useCallback((field: string, value: unknown) => {
    setState(prev => ({
      ...prev,
      outputs: { ...prev.outputs, [field]: value }
    }));
  }, []);

  // Progress calculation
  const getProgress = () => {
    const steps = {
      scenario: state.scenario.name.length > 0,
      population: state.population.include.conditions.length > 0 ||
                  state.population.include.medications.length > 0 ||
                  state.population.demographics.ageMin !== 18 ||
                  state.population.demographics.ageMax !== 99,
      logic: state.rules.some(r => r.signal !== null || r.useCustomExpression),
      outputs: state.outputs.decisions.length > 0 || state.outputs.features.length > 0,
      audit: state.audit.intent.length > 0 || state.audit.rationale.length > 0
    };
    return steps;
  };

  const progress = getProgress();

  // For backward compatibility with LogicRulesSection
  const conditions = state.rules;

  return (
    <div className="psdl-builder">
      {/* Progress Bar */}
      <div className="progress-bar flex gap-1 mb-6 px-3 pt-3 pb-6 bg-background-secondary rounded-lg">
        {[
          { id: 'scenario', label: 'Scenario', done: progress.scenario },
          { id: 'population', label: 'Population', done: progress.population },
          { id: 'logic', label: 'Logic', done: progress.logic },
          { id: 'audit', label: 'Audit', done: progress.audit },
          { id: 'outputs', label: 'Outputs', done: progress.outputs },
        ].map((step) => (
          <div key={step.id} className="flex-1 relative">
            <div className={`h-1 rounded-full transition-colors ${step.done ? 'bg-accent-success' : 'bg-background-tertiary'}`} />
            <span className={`absolute top-3 left-0 text-[10px] font-mono uppercase tracking-wider ${step.done ? 'text-accent-success' : 'text-muted'}`}>
              {step.label}
            </span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_340px] xl:grid-cols-[minmax(0,1fr)_400px] gap-6">
        {/* Left: Builder Sections */}
        <div className="builder-sections space-y-4">
          {/* Section 1: Scenario */}
          <ScenarioSection
            scenario={state.scenario}
            onChange={updateScenario}
          />

          {/* Section 2: Population */}
          <PopulationSection
            population={state.population}
            onUpdateItems={updatePopulation}
            onUpdateDemographics={updateDemographics}
          />

          {/* Section 3: Logic Rules */}
          <LogicRulesSection
            conditions={conditions}
            allRules={state.rules}
            onAddCondition={addRule}
            onRemoveCondition={removeRule}
            onUpdateCondition={updateRule}
          />

          {/* Section 4: Audit */}
          <div className="section-panel bg-background-secondary rounded-lg">
            <div className="section-header flex items-center gap-3 px-4 py-3 bg-background-tertiary rounded-t-lg">
              <span className="section-number w-7 h-7 flex items-center justify-center bg-accent-cyan/20 rounded font-mono text-sm font-bold text-accent-cyan">04</span>
              <span className="section-title text-sm font-semibold text-foreground">Audit</span>
              <Tooltip content={GLOSSARY.audit} />
            </div>
            <div className="section-body px-4 py-4 space-y-4">
              <div className="form-group">
                <div className="flex items-center gap-1.5 mb-2">
                  <label className="form-label text-sm font-semibold text-foreground-secondary">Intent</label>
                  <Tooltip content={GLOSSARY.intent} />
                </div>
                <textarea
                  className="form-input w-full px-3 py-2.5 bg-background rounded-md text-foreground text-sm focus:ring-2 focus:ring-accent/30 outline-none transition-all placeholder:text-muted/50 resize-none"
                  rows={2}
                  placeholder="Why does this scenario exist? What clinical need does it address?"
                  value={state.audit.intent}
                  onChange={(e) => updateAudit('intent', e.target.value)}
                />
              </div>
              <div className="form-group">
                <div className="flex items-center gap-1.5 mb-2">
                  <label className="form-label text-sm font-semibold text-foreground-secondary">Rationale</label>
                  <Tooltip content={GLOSSARY.rationale} />
                </div>
                <textarea
                  className="form-input w-full px-3 py-2.5 bg-background rounded-md text-foreground text-sm focus:ring-2 focus:ring-accent/30 outline-none transition-all placeholder:text-muted/50 resize-none"
                  rows={2}
                  placeholder="Clinical reasoning and evidence basis for the thresholds and logic"
                  value={state.audit.rationale}
                  onChange={(e) => updateAudit('rationale', e.target.value)}
                />
              </div>
              <div className="form-group">
                <div className="flex items-center gap-1.5 mb-2">
                  <label className="form-label text-sm font-semibold text-foreground-secondary">Provenance</label>
                  <Tooltip content={GLOSSARY.provenance} />
                </div>
                <input
                  type="text"
                  className="form-input w-full px-3 py-2.5 bg-background rounded-md text-foreground text-sm focus:ring-2 focus:ring-accent/30 outline-none transition-all placeholder:text-muted/50"
                  placeholder="Author, institution, guidelines referenced"
                  value={state.audit.provenance}
                  onChange={(e) => updateAudit('provenance', e.target.value)}
                />
              </div>
              <div className="bg-background rounded-lg p-3 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-foreground-secondary">Created</span>
                  <span className="text-foreground font-mono">{new Date().toISOString().split('T')[0]}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-foreground-secondary">Vocabulary</span>
                  <span className="text-foreground font-mono text-xs">{vocabVersion}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Section 5: Outputs */}
          <OutputsSection
            outputs={state.outputs}
            rules={state.rules}
            onUpdateOutputs={updateOutputs}
          />
        </div>

        {/* Right: Preview Panel */}
        <BuilderPreview
          state={state}
          onValidationChange={onValidationChange}
          onContinue={onContinue}
          isValidating={isValidating}
        />
      </div>
    </div>
  );
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
        whenExpr = 'true';  // Fallback
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
