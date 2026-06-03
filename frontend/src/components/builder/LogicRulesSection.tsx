'use client';

import { useState, useCallback, useRef } from 'react';
import type { LogicRule, Signal } from './PSDLBuilder';
import { METRICS, OPERATORS, SEVERITIES } from './PSDLBuilder';
import Tooltip, { GLOSSARY } from './Tooltip';

interface LogicRulesSectionProps {
  conditions: LogicRule[];
  allRules: LogicRule[];
  onAddCondition: () => void;
  onRemoveCondition: (id: number) => void;
  onUpdateCondition: (id: number, field: string, value: unknown) => void;
}

export default function LogicRulesSection({
  conditions,
  allRules,
  onAddCondition,
  onRemoveCondition,
  onUpdateCondition
}: LogicRulesSectionProps) {
  const [searchResults, setSearchResults] = useState<Record<string, Signal[]>>({});
  const [showResults, setShowResults] = useState<Record<string, boolean>>({});
  const [expandedRules, setExpandedRules] = useState<Set<number>>(new Set());
  const searchTimeoutRef = useRef<NodeJS.Timeout>();

  const handleSignalSearch = useCallback(async (query: string, ruleId: number, field: 'signal' | 'secondSignal') => {
    const key = `${ruleId}-${field}`;

    if (query.length < 2) {
      setShowResults(prev => ({ ...prev, [key]: false }));
      return;
    }

    clearTimeout(searchTimeoutRef.current);
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        let endpoint = `http://localhost:8200/api/vocabulary/semantic/search?q=${encodeURIComponent(query)}&limit=10`;
        let resp = await fetch(endpoint);

        if (!resp.ok) {
          endpoint = `http://localhost:8200/api/vocabulary/search?q=${encodeURIComponent(query)}&limit=10`;
          resp = await fetch(endpoint);
        }

        const data = await resp.json();
        setSearchResults(prev => ({ ...prev, [key]: data.results || [] }));
        setShowResults(prev => ({ ...prev, [key]: true }));
      } catch {
        setSearchResults(prev => ({ ...prev, [key]: [] }));
        setShowResults(prev => ({ ...prev, [key]: true }));
      }
    }, 300);
  }, []);

  const selectSignal = useCallback((ruleId: number, field: 'signal' | 'secondSignal', signal: Signal) => {
    const key = `${ruleId}-${field}`;
    onUpdateCondition(ruleId, field, signal);

    if (field === 'signal') {
      const name = signal.concept_name.toLowerCase();
      if (name.includes('glucose')) {
        onUpdateCondition(ruleId, 'value', 70);
        onUpdateCondition(ruleId, 'operator', 'lt');
      } else if (name.includes('creatinine')) {
        onUpdateCondition(ruleId, 'value', 1.5);
        onUpdateCondition(ruleId, 'operator', 'gt');
      } else if (name.includes('heart rate') || name.includes('pulse')) {
        onUpdateCondition(ruleId, 'value', 100);
        onUpdateCondition(ruleId, 'operator', 'gt');
      }
    }

    setShowResults(prev => ({ ...prev, [key]: false }));
  }, [onUpdateCondition]);

  const clearSignal = useCallback((ruleId: number, field: 'signal' | 'secondSignal') => {
    onUpdateCondition(ruleId, field, null);
  }, [onUpdateCondition]);

  const toggleRuleExpansion = useCallback((ruleId: number) => {
    setExpandedRules(prev => {
      const newSet = new Set(prev);
      if (newSet.has(ruleId)) {
        newSet.delete(ruleId);
      } else {
        newSet.add(ruleId);
      }
      return newSet;
    });
  }, []);

  const insertRuleReference = useCallback((ruleId: number, refRuleName: string) => {
    const rule = conditions.find(r => r.id === ruleId);
    if (!rule) return;

    const currentExpr = rule.customExpression;
    const needsSpace = currentExpr && !currentExpr.endsWith(' ') && !currentExpr.endsWith('(');
    const newExpr = currentExpr ? `${currentExpr}${needsSpace ? ' ' : ''}${refRuleName}` : refRuleName;
    onUpdateCondition(ruleId, 'customExpression', newExpr);
  }, [conditions, onUpdateCondition]);

  const insertOperator = useCallback((ruleId: number, op: string) => {
    const rule = conditions.find(r => r.id === ruleId);
    if (!rule) return;

    const currentExpr = rule.customExpression;
    const needsSpace = currentExpr && !currentExpr.endsWith(' ') && !currentExpr.endsWith('(');
    const newExpr = currentExpr ? `${currentExpr}${needsSpace ? ' ' : ''}${op} ` : `${op} `;
    onUpdateCondition(ruleId, 'customExpression', newExpr);
  }, [conditions, onUpdateCondition]);

  const renderSignalInput = (rule: LogicRule, field: 'signal' | 'secondSignal', className?: string) => {
    const key = `${rule.id}-${field}`;
    const signal = field === 'signal' ? rule.signal : rule.secondSignal;
    const results = searchResults[key] || [];
    const isShowingResults = showResults[key];

    if (signal) {
      return (
        <div
          className={`flex items-center gap-2 px-3 py-2 bg-accent-cyan/10 rounded-md cursor-pointer hover:bg-accent-cyan/15 transition-colors ${className}`}
          onClick={() => clearSignal(rule.id, field)}
        >
          <span className="font-mono text-sm text-accent-cyan truncate">{signal.concept_name}</span>
          <span className="text-sm text-muted ml-auto shrink-0">x</span>
        </div>
      );
    }

    return (
      <div className={`relative ${className}`}>
        <input
          type="text"
          className="w-full px-3 py-2 bg-background rounded-md text-foreground text-sm focus:ring-2 focus:ring-accent/30 outline-none placeholder:text-muted/50"
          placeholder="Search signal..."
          onInput={(e) => handleSignalSearch((e.target as HTMLInputElement).value, rule.id, field)}
          onBlur={() => setTimeout(() => setShowResults(prev => ({ ...prev, [key]: false })), 200)}
          onFocus={(e) => {
            if ((e.target as HTMLInputElement).value.length >= 2) {
              setShowResults(prev => ({ ...prev, [key]: true }));
            }
          }}
        />
        {isShowingResults && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-background-elevated rounded-lg shadow-lg max-h-[240px] overflow-y-auto z-50 border border-border">
            {results.length > 0 ? (
              results.map(r => (
                <div
                  key={r.concept_id}
                  className="px-3 py-2 cursor-pointer hover:bg-background-tertiary transition-colors"
                  onClick={() => selectSignal(rule.id, field, r)}
                >
                  <div className="text-sm text-foreground">{r.concept_name}</div>
                  <div className="flex flex-wrap items-center gap-1.5 mt-0.5">
                    <span className="font-mono text-xs px-1.5 py-0.5 bg-accent-cyan/10 text-accent-cyan rounded">{r.vocabulary_id || 'LOINC'}</span>
                    {r.category && (
                      <span className="text-xs px-1.5 py-0.5 bg-accent-purple/10 text-accent-purple rounded capitalize">{r.category.replace(/_/g, ' ')}</span>
                    )}
                    {r.abbreviations && r.abbreviations.length > 0 && (
                      <span className="text-xs text-muted truncate" title={r.abbreviations.join(', ')}>also: {r.abbreviations.slice(0, 3).join(', ')}</span>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="px-3 py-2 text-sm text-foreground-secondary italic">No results</div>
            )}
          </div>
        )}
      </div>
    );
  };

  // Get other rules for reference (exclude current rule)
  const getOtherRules = (currentRuleId: number) => {
    return allRules.filter(r => r.id !== currentRuleId && (r.signal || r.customExpression));
  };

  return (
    <div className="section-panel bg-background-secondary rounded-lg">
      <div className="section-header flex items-center gap-3 px-4 py-3 bg-background-tertiary rounded-t-lg">
        <span className="section-number w-7 h-7 flex items-center justify-center bg-accent-cyan/20 rounded font-mono text-sm font-bold text-accent-cyan">03</span>
        <span className="section-title text-sm font-semibold text-foreground">Logic Rules</span>
        <Tooltip content={GLOSSARY.logicRules} />
        <span className="text-xs text-muted ml-auto">Each rule has a name, condition, and severity</span>
      </div>
      <div className="section-body px-4 py-4">
        <div className="space-y-3">
          {/* Empty State */}
          {conditions.length === 0 && (
            <div className="text-center py-8 text-muted">
              <div className="text-2xl mb-2 opacity-30">+</div>
              <div className="text-sm">Add rules to define clinical logic</div>
              <div className="text-xs mt-1 text-muted/70">Rules can reference signals or other rules</div>
            </div>
          )}

          {/* Rules */}
          {conditions.map((rule) => {
            const metricConfig = METRICS[rule.metric];
            const unit = rule.signal?.typical_units?.[0]?.code || '';
            const valueUnit = rule.metric === 'percent_change' ? '%' : unit;
            const isExpanded = expandedRules.has(rule.id);
            const otherRules = getOtherRules(rule.id);

            return (
              <div key={rule.id} className="rule-card bg-background rounded-lg">
                {/* Rule Header */}
                <div className="flex items-center justify-between px-4 py-3 bg-background-tertiary/50">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="flex items-center gap-1">
                      <input
                        type="text"
                        className="font-mono text-sm font-semibold text-accent-cyan bg-transparent border-none outline-none focus:ring-0 w-36"
                        value={rule.name}
                        onChange={(e) => onUpdateCondition(rule.id, 'name', e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
                        placeholder="rule_name"
                        title="Unique rule identifier (snake_case)"
                      />
                      <Tooltip content={GLOSSARY.ruleName} />
                    </div>
                    <div className="flex items-center gap-1">
                      <select
                        className={`px-2.5 py-1 rounded-full text-xs font-semibold cursor-pointer outline-none ${
                          rule.severity === 'low' ? 'bg-accent-success/10 text-accent-success' :
                          rule.severity === 'medium' ? 'bg-accent-warning/10 text-accent-warning' :
                          'bg-accent-danger/10 text-accent-danger'
                        }`}
                        value={rule.severity}
                        onChange={(e) => onUpdateCondition(rule.id, 'severity', e.target.value)}
                      >
                        {SEVERITIES.map(s => (
                          <option key={s.value} value={s.value}>{s.label}</option>
                        ))}
                      </select>
                      <Tooltip content={GLOSSARY.severity} />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      className="text-muted hover:text-foreground transition-colors text-sm px-2"
                      onClick={() => toggleRuleExpansion(rule.id)}
                    >
                      {isExpanded ? '▼' : '▶'} Details
                    </button>
                    <button
                      className="text-muted hover:text-accent-danger transition-colors text-sm px-2"
                      onClick={() => onRemoveCondition(rule.id)}
                    >
                      Remove
                    </button>
                  </div>
                </div>

                {/* Rule Body */}
                <div className="p-4">
                  {/* Mode Toggle */}
                  <div className="flex items-center gap-3 mb-3">
                    <label className="flex items-center gap-2 text-sm text-foreground-secondary cursor-pointer">
                      <input
                        type="checkbox"
                        className="cursor-pointer accent-accent"
                        checked={rule.useCustomExpression}
                        onChange={(e) => onUpdateCondition(rule.id, 'useCustomExpression', e.target.checked)}
                      />
                      <span className="font-mono text-xs">Composite Rule</span>
                    </label>
                    <Tooltip content={GLOSSARY.compositeRule} />
                    <span className="text-xs text-muted">
                      {rule.useCustomExpression ? 'Reference other rules' : 'Define signal condition'}
                    </span>
                  </div>

                  {!rule.useCustomExpression ? (
                    /* Signal-based condition */
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-foreground-secondary uppercase">When</span>

                      {renderSignalInput(rule, 'signal', 'flex-1 min-w-[160px]')}

                      <select
                        className="px-3 py-2 bg-background-tertiary rounded-md text-foreground text-sm cursor-pointer outline-none"
                        value={rule.metric}
                        onChange={(e) => onUpdateCondition(rule.id, 'metric', e.target.value)}
                      >
                        {Object.entries(METRICS).map(([key, m]) => (
                          <option key={key} value={key}>{m.label}</option>
                        ))}
                      </select>

                      {metricConfig.needsWindow && (
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            className="w-14 px-2 py-2 bg-background-tertiary rounded-md text-foreground text-sm text-center outline-none"
                            value={rule.window.value}
                            onChange={(e) => onUpdateCondition(rule.id, 'window.value', parseInt(e.target.value) || 0)}
                          />
                          <select
                            className="px-2 py-2 bg-background-tertiary rounded-md text-foreground text-sm cursor-pointer outline-none"
                            value={rule.window.unit}
                            onChange={(e) => onUpdateCondition(rule.id, 'window.unit', e.target.value)}
                          >
                            <option value="m">min</option>
                            <option value="h">hr</option>
                            <option value="d">day</option>
                          </select>
                        </div>
                      )}

                      {metricConfig.needsSecondSignal && renderSignalInput(rule, 'secondSignal', 'min-w-[140px]')}

                      <select
                        className="px-3 py-2 bg-background-tertiary rounded-md text-foreground text-sm cursor-pointer outline-none"
                        value={rule.operator}
                        onChange={(e) => onUpdateCondition(rule.id, 'operator', e.target.value)}
                      >
                        {OPERATORS.map(op => (
                          <option key={op.value} value={op.value}>{op.label}</option>
                        ))}
                      </select>

                      <input
                        type="number"
                        className="w-20 px-3 py-2 bg-background-tertiary rounded-md text-foreground text-sm text-center font-semibold outline-none"
                        value={rule.value}
                        step="any"
                        onChange={(e) => onUpdateCondition(rule.id, 'value', parseFloat(e.target.value) || 0)}
                      />

                      {valueUnit && <span className="text-sm text-foreground-secondary">{valueUnit}</span>}
                    </div>
                  ) : (
                    /* Composite expression mode */
                    <div className="space-y-2">
                      <p className="text-xs text-muted">Combine rules with AND, OR, and parentheses</p>

                      {/* Available rule chips */}
                      {otherRules.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {otherRules.map(r => (
                            <button
                              key={r.id}
                              className="font-mono text-xs px-2.5 py-1 bg-accent-cyan/10 text-accent-cyan rounded hover:bg-accent-cyan/20 transition-colors"
                              onClick={() => insertRuleReference(rule.id, r.name)}
                            >
                              {r.name}
                            </button>
                          ))}
                          <button
                            className="font-mono text-xs px-2.5 py-1 bg-accent-warning/10 text-accent-warning rounded hover:bg-accent-warning/20 transition-colors font-semibold"
                            onClick={() => insertOperator(rule.id, 'AND')}
                          >
                            AND
                          </button>
                          <button
                            className="font-mono text-xs px-2.5 py-1 bg-accent-warning/10 text-accent-warning rounded hover:bg-accent-warning/20 transition-colors font-semibold"
                            onClick={() => insertOperator(rule.id, 'OR')}
                          >
                            OR
                          </button>
                          <button
                            className="font-mono text-xs px-2.5 py-1 bg-background-tertiary text-foreground-secondary rounded hover:bg-background transition-colors"
                            onClick={() => {
                              const expr = rule.customExpression;
                              onUpdateCondition(rule.id, 'customExpression', expr ? `(${expr})` : '(');
                            }}
                          >
                            ( )
                          </button>
                        </div>
                      )}

                      {otherRules.length === 0 && (
                        <div className="text-xs text-accent-warning bg-accent-warning/10 px-3 py-2 rounded">
                          Add other rules first to reference them here
                        </div>
                      )}

                      <input
                        type="text"
                        className="w-full px-3 py-2.5 bg-background-tertiary rounded-md text-foreground font-mono text-sm focus:ring-2 focus:ring-accent/30 outline-none"
                        placeholder="aki_stage1 AND bun_rising"
                        value={rule.customExpression}
                        onChange={(e) => onUpdateCondition(rule.id, 'customExpression', e.target.value)}
                      />

                      {/* Validation */}
                      {rule.customExpression && (() => {
                        const validNames = otherRules.map(r => r.name);
                        const tokens = rule.customExpression.match(/[a-z_0-9]+/gi) || [];
                        const invalidTokens = tokens.filter(t =>
                          !['AND', 'OR', 'and', 'or'].includes(t) && !validNames.includes(t)
                        );
                        const opens = (rule.customExpression.match(/\(/g) || []).length;
                        const closes = (rule.customExpression.match(/\)/g) || []).length;

                        if (invalidTokens.length > 0) {
                          return <div className="text-xs text-accent-danger">Unknown: {invalidTokens.join(', ')}</div>;
                        }
                        if (opens !== closes) {
                          return <div className="text-xs text-accent-danger">Unbalanced parentheses</div>;
                        }
                        return <div className="text-xs text-accent-success">Expression valid</div>;
                      })()}
                    </div>
                  )}

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-border/30 space-y-3">
                      <div>
                        <label className="block text-xs font-semibold text-foreground-secondary mb-1.5">Description</label>
                        <input
                          type="text"
                          className="w-full px-3 py-2 bg-background-tertiary rounded-md text-foreground text-sm focus:ring-2 focus:ring-accent/30 outline-none placeholder:text-muted/50"
                          placeholder="What does this rule detect?"
                          value={rule.description}
                          onChange={(e) => onUpdateCondition(rule.id, 'description', e.target.value)}
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-foreground-secondary mb-1.5">Recommendation</label>
                        <input
                          type="text"
                          className="w-full px-3 py-2 bg-background-tertiary rounded-md text-foreground text-sm focus:ring-2 focus:ring-accent/30 outline-none placeholder:text-muted/50"
                          placeholder="Clinical action to take when triggered"
                          value={rule.recommendation}
                          onChange={(e) => onUpdateCondition(rule.id, 'recommendation', e.target.value)}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Add Button */}
          <button
            className="w-full py-3 text-sm font-semibold bg-accent/10 text-accent hover:bg-accent hover:text-white rounded-lg transition-colors border border-accent/30 hover:border-accent"
            onClick={onAddCondition}
          >
            + Add Rule
          </button>
        </div>
      </div>
    </div>
  );
}
