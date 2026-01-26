'use client';

import { useState, useCallback } from 'react';
import type { LogicRule, OutputDecision, OutputFeature } from './PSDLBuilder';
import { METRICS } from './PSDLBuilder';
import Tooltip, { GLOSSARY } from './Tooltip';

interface OutputsSectionProps {
  outputs: {
    decisions: OutputDecision[];
    features: OutputFeature[];
    includeTimestamp: boolean;
  };
  rules: LogicRule[];
  onUpdateOutputs: (field: string, value: unknown) => void;
}

// Helper to get trend ID for a rule (matches PSDLBuilder.tsx)
function getTrendId(rule: LogicRule): string {
  if (!rule.signal) return '';
  const signalId = rule.signal.concept_name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/_+$/, '');
  const metric = METRICS[rule.metric]?.expr || rule.metric;
  // All metrics get a trend - 'current' uses last()
  if (rule.metric === 'current') return `${signalId}_current`;
  return `${signalId}_${metric}_${rule.window.value}${rule.window.unit}`;
}

export default function OutputsSection({ outputs, rules, onUpdateOutputs }: OutputsSectionProps) {
  const [newDecisionName, setNewDecisionName] = useState('');
  const [newDecisionRule, setNewDecisionRule] = useState('');
  const [newFeatureName, setNewFeatureName] = useState('');
  const [newFeatureTrend, setNewFeatureTrend] = useState('');

  // Get valid rules (those with signals or custom expressions)
  const validRules = rules.filter(r => r.signal || (r.useCustomExpression && r.customExpression));

  // Get trends (all rules with signals now have trends, including 'current' which uses last())
  const trends = rules.filter(r => r.signal && !r.useCustomExpression);

  const addDecision = useCallback(() => {
    if (!newDecisionName || !newDecisionRule) return;

    const newDecision: OutputDecision = {
      name: newDecisionName,
      fromRule: newDecisionRule
    };

    onUpdateOutputs('decisions', [...outputs.decisions, newDecision]);
    setNewDecisionName('');
    setNewDecisionRule('');
  }, [newDecisionName, newDecisionRule, outputs.decisions, onUpdateOutputs]);

  const removeDecision = useCallback((name: string) => {
    onUpdateOutputs('decisions', outputs.decisions.filter(d => d.name !== name));
  }, [outputs.decisions, onUpdateOutputs]);

  const addFeature = useCallback(() => {
    if (!newFeatureName || !newFeatureTrend) return;

    const newFeature: OutputFeature = {
      name: newFeatureName,
      fromTrend: newFeatureTrend
    };

    onUpdateOutputs('features', [...outputs.features, newFeature]);
    setNewFeatureName('');
    setNewFeatureTrend('');
  }, [newFeatureName, newFeatureTrend, outputs.features, onUpdateOutputs]);

  const removeFeature = useCallback((name: string) => {
    onUpdateOutputs('features', outputs.features.filter(f => f.name !== name));
  }, [outputs.features, onUpdateOutputs]);

  return (
    <div className="section-panel bg-background-secondary rounded-lg">
      <div className="section-header flex items-center gap-3 px-4 py-3 bg-background-tertiary rounded-t-lg">
        <span className="section-number w-7 h-7 flex items-center justify-center bg-accent-cyan/20 rounded font-mono text-sm font-bold text-accent-cyan">05</span>
        <span className="section-title text-sm font-semibold text-foreground">Outputs</span>
        <Tooltip content={GLOSSARY.outputs} />
      </div>
      <div className="section-body px-4 py-4">
        <p className="text-sm text-foreground-secondary mb-4">
          Define what this scenario exposes to downstream systems.
        </p>

        {/* Decisions */}
        <div className="mb-4">
          <div className="flex justify-between items-center mb-2">
            <span className="flex items-center gap-1.5 text-sm font-semibold text-accent-purple">
              Decisions
              <Tooltip content={GLOSSARY.decisions} />
            </span>
            <span className="text-xs text-foreground-secondary">Boolean outputs from logic rules</span>
          </div>

          {/* Existing Decisions */}
          {outputs.decisions.length > 0 && (
            <div className="space-y-1.5 mb-3">
              {outputs.decisions.map(d => (
                <div key={d.name} className="flex items-center justify-between px-3 py-2 bg-background rounded-md group">
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-sm text-accent-cyan truncate">{d.name}</div>
                    <div className="font-mono text-xs text-muted">from: {d.fromRule}</div>
                  </div>
                  <button
                    className="opacity-0 group-hover:opacity-100 text-muted hover:text-accent-danger transition-all text-sm px-2"
                    onClick={() => removeDecision(d.name)}
                  >
                    x
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add Decision */}
          {validRules.length > 0 ? (
            <div className="flex gap-2 items-center">
              <input
                type="text"
                className="flex-1 min-w-[100px] px-3 py-2 bg-background rounded-md text-foreground font-mono text-sm focus:ring-2 focus:ring-accent/30 outline-none placeholder:text-muted/50"
                placeholder="output_name"
                value={newDecisionName}
                onChange={(e) => setNewDecisionName(e.target.value)}
              />
              <select
                className="flex-[2] px-3 py-2 bg-background-tertiary rounded-md text-foreground text-sm cursor-pointer outline-none"
                value={newDecisionRule}
                onChange={(e) => setNewDecisionRule(e.target.value)}
              >
                <option value="">Select rule...</option>
                {validRules.map((rule) => (
                  <option key={rule.id} value={rule.name}>
                    {rule.name} ({rule.severity})
                  </option>
                ))}
              </select>
              <button
                className="w-9 h-9 flex items-center justify-center bg-accent/10 text-accent rounded-md text-lg font-medium hover:bg-accent hover:text-background transition-colors"
                onClick={addDecision}
              >
                +
              </button>
            </div>
          ) : (
            <p className="text-sm text-foreground-secondary px-1">Add logic rules to enable decisions</p>
          )}
        </div>

        {/* Features */}
        <div className="mb-4">
          <div className="flex justify-between items-center mb-2">
            <span className="flex items-center gap-1.5 text-sm font-semibold text-accent-purple">
              Features
              <Tooltip content={GLOSSARY.features} />
            </span>
            <span className="text-xs text-foreground-secondary">Numeric outputs from trends</span>
          </div>

          {/* Existing Features */}
          {outputs.features.length > 0 && (
            <div className="space-y-1.5 mb-3">
              {outputs.features.map(f => (
                <div key={f.name} className="flex items-center justify-between px-3 py-2 bg-background rounded-md group">
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-sm text-accent-cyan truncate">{f.name}</div>
                    <div className="font-mono text-xs text-muted">from: {f.fromTrend}</div>
                  </div>
                  <button
                    className="opacity-0 group-hover:opacity-100 text-muted hover:text-accent-danger transition-all text-sm px-2"
                    onClick={() => removeFeature(f.name)}
                  >
                    x
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add Feature */}
          {trends.length > 0 ? (
            <div className="flex gap-2 items-center">
              <input
                type="text"
                className="flex-1 min-w-[100px] px-3 py-2 bg-background rounded-md text-foreground font-mono text-sm focus:ring-2 focus:ring-accent/30 outline-none placeholder:text-muted/50"
                placeholder="feature_name"
                value={newFeatureName}
                onChange={(e) => setNewFeatureName(e.target.value)}
              />
              <select
                className="flex-[2] px-3 py-2 bg-background-tertiary rounded-md text-foreground text-sm cursor-pointer outline-none"
                value={newFeatureTrend}
                onChange={(e) => setNewFeatureTrend(e.target.value)}
              >
                <option value="">Select trend...</option>
                {trends.map((rule) => {
                  const trendId = getTrendId(rule);
                  const signalName = rule.signal?.concept_name || '';
                  const metricLabel = METRICS[rule.metric]?.label || rule.metric;
                  return (
                    <option key={rule.id} value={trendId}>
                      {trendId} ({signalName} {metricLabel})
                    </option>
                  );
                })}
              </select>
              <button
                className="w-9 h-9 flex items-center justify-center bg-accent/10 text-accent rounded-md text-lg font-medium hover:bg-accent hover:text-background transition-colors"
                onClick={addFeature}
              >
                +
              </button>
            </div>
          ) : (
            <p className="text-sm text-foreground-secondary px-1">Add signal-based rules to enable features</p>
          )}
        </div>

        {/* Evidence */}
        <div className="p-3 bg-background rounded-lg">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-semibold text-accent-purple">Evidence</span>
            <span className="text-xs text-foreground-secondary">Supporting metadata</span>
          </div>
          <label className="flex items-center gap-2.5 text-sm text-foreground-secondary cursor-pointer">
            <input
              type="checkbox"
              className="w-4 h-4 cursor-pointer accent-accent"
              checked={outputs.includeTimestamp}
              onChange={(e) => onUpdateOutputs('includeTimestamp', e.target.checked)}
            />
            <span>Include evaluation timestamp</span>
          </label>
        </div>
      </div>
    </div>
  );
}
