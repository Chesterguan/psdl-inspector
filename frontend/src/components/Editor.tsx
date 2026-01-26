'use client';

import { useRef, useEffect, useState, useMemo } from 'react';
import { FileCode, Copy, Check } from 'lucide-react';

// PSDL skeleton template with helpful comments
const PSDL_SKELETON = `# PSDL Scenario Template
# Replace placeholders with your clinical scenario details

scenario: your_scenario_name
version: "0.3.1"
description: "Brief description of what this scenario detects"

# SIGNALS: Define data inputs from EHR/monitoring systems
# Each signal maps to a clinical concept (OMOP concept_id recommended)
signals:
  SignalName:
    ref: semantic_reference       # e.g., heart_rate, blood_pressure
    concept_id: 12345             # OMOP concept ID (optional but recommended)
    unit: unit_of_measure         # e.g., bpm, mmHg, mg/dL

  # Add more signals as needed:
  # AnotherSignal:
  #   ref: another_reference
  #   concept_id: 67890
  #   unit: unit

# TRENDS: Compute derived values from signals over time windows
# Supported functions: delta(), avg(), min(), max(), last()
trends:
  trend_name:
    expr: delta(SignalName, 24h)  # Change over 24 hours
    description: "Human-readable description"

  # Examples:
  # signal_avg_1h:
  #   expr: avg(SignalName, 1h)
  #   description: "1-hour average"
  #
  # signal_current:
  #   expr: last(SignalName)
  #   description: "Most recent value"

# LOGIC: Define clinical decision rules
# Reference trends (not signals directly) in conditions
logic:
  rule_name:
    when: trend_name >= threshold   # Condition using trend
    severity: medium                # low, medium, high, critical
    description: "What this rule detects"

  # Compound rules can reference other rules:
  # combined_rule:
  #   when: rule_name AND another_rule
  #   severity: high
  #   description: "Combined condition"

# OUTPUTS (optional): Expose results to downstream systems
outputs:
  decision:
    alert_flag:
      type: boolean
      from: logic.rule_name

  features:
    trend_value:
      type: numeric
      from: trends.trend_name

  evidence:
    evaluation_time:
      type: timestamp
`;

interface EditorProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
  readOnly?: boolean;
  showLineNumbers?: boolean;
  showTemplateButton?: boolean;
}

export default function Editor({
  value,
  onChange,
  className = '',
  readOnly = false,
  showLineNumbers = true,
  showTemplateButton = true
}: EditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lineNumbersRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  // Calculate line numbers
  const lineNumbers = useMemo(() => {
    const lines = value.split('\n');
    return lines.map((_, i) => i + 1);
  }, [value]);

  // Sync scroll between textarea and line numbers
  const handleScroll = () => {
    if (textareaRef.current && lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  };

  // Auto-resize textarea to fit content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.max(textareaRef.current.scrollHeight, 400)}px`;
    }
  }, [value]);

  // Handle tab key for indentation
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const target = e.target as HTMLTextAreaElement;
      const start = target.selectionStart;
      const end = target.selectionEnd;
      const newValue = value.substring(0, start) + '  ' + value.substring(end);
      onChange(newValue);
      // Move cursor after the inserted spaces
      setTimeout(() => {
        target.selectionStart = target.selectionEnd = start + 2;
      }, 0);
    }
  };

  const insertTemplate = () => {
    onChange(PSDL_SKELETON);
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className={`yaml-editor-container ${className}`}>
      {/* Toolbar */}
      {(showTemplateButton || !readOnly) && (
        <div className="flex items-center justify-between px-3 py-2 bg-background-tertiary border-b border-border rounded-t-lg">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted uppercase tracking-wide">YAML Editor</span>
            {value && (
              <span className="text-xs text-muted">
                {lineNumbers.length} lines
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {showTemplateButton && !readOnly && (
              <button
                onClick={insertTemplate}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-foreground-secondary hover:text-foreground bg-background hover:bg-background-secondary rounded-md border border-border transition-colors"
                title="Insert PSDL template"
              >
                <FileCode className="w-3.5 h-3.5" />
                Insert Template
              </button>
            )}
            <button
              onClick={copyToClipboard}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-foreground-secondary hover:text-foreground bg-background hover:bg-background-secondary rounded-md border border-border transition-colors"
              title="Copy to clipboard"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-accent-success" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  Copy
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Editor with line numbers */}
      <div className="editor-wrapper flex relative">
        {/* Line Numbers */}
        {showLineNumbers && (
          <div
            ref={lineNumbersRef}
            className="line-numbers flex-shrink-0 w-12 py-4 pr-2 text-right bg-background-secondary border-r border-border overflow-hidden select-none"
            style={{ fontFamily: "'JetBrains Mono', 'SF Mono', Monaco, monospace" }}
          >
            {lineNumbers.map((num) => (
              <div
                key={num}
                className="text-xs leading-7 text-muted"
              >
                {num}
              </div>
            ))}
          </div>
        )}

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onScroll={handleScroll}
          readOnly={readOnly}
          spellCheck={false}
          placeholder="Start typing your PSDL scenario, or click 'Insert Template' for a starter skeleton..."
          className={`
            yaml-editor
            flex-1 w-full h-full min-h-[400px]
            px-4 py-4
            font-mono text-sm leading-7
            resize-none
            focus:outline-none
            transition-colors
            bg-background text-foreground-secondary
            placeholder:text-muted/40
            ${showLineNumbers ? 'rounded-none' : 'rounded-lg border border-border'}
            ${!showTemplateButton && !readOnly ? 'rounded-t-lg' : ''}
          `}
          style={{
            fontFamily: "'JetBrains Mono', 'SF Mono', Monaco, monospace",
            tabSize: 2,
          }}
        />
      </div>

      <style jsx>{`
        .yaml-editor-container {
          position: relative;
          border: 1px solid var(--border);
          border-radius: 0.5rem;
          overflow: hidden;
        }
        .editor-wrapper {
          max-height: calc(100vh - 300px);
          overflow: hidden;
        }
        .yaml-editor {
          white-space: pre;
          word-wrap: normal;
          overflow-x: auto;
          overflow-y: auto;
        }
        .line-numbers {
          overflow-y: hidden;
          pointer-events: none;
        }
        .yaml-editor::-webkit-scrollbar {
          width: 10px;
          height: 10px;
        }
        .yaml-editor::-webkit-scrollbar-track {
          background: var(--background-secondary);
        }
        .yaml-editor::-webkit-scrollbar-thumb {
          background: var(--border);
          border-radius: 5px;
        }
        .yaml-editor::-webkit-scrollbar-thumb:hover {
          background: var(--muted);
        }
      `}</style>
    </div>
  );
}

// Export the skeleton for use elsewhere
export { PSDL_SKELETON };
