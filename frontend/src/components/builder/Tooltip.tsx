'use client';

import { useState, useRef, useEffect } from 'react';

interface TooltipProps {
  content: string;
  children?: React.ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
}

export default function Tooltip({ content, children, position = 'top' }: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [coords, setCoords] = useState({ x: 0, y: 0 });
  const triggerRef = useRef<HTMLSpanElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isVisible && triggerRef.current && tooltipRef.current) {
      const triggerRect = triggerRef.current.getBoundingClientRect();
      const tooltipRect = tooltipRef.current.getBoundingClientRect();

      let x = 0;
      let y = 0;

      switch (position) {
        case 'top':
          x = triggerRect.left + (triggerRect.width / 2) - (tooltipRect.width / 2);
          y = triggerRect.top - tooltipRect.height - 8;
          break;
        case 'bottom':
          x = triggerRect.left + (triggerRect.width / 2) - (tooltipRect.width / 2);
          y = triggerRect.bottom + 8;
          break;
        case 'left':
          x = triggerRect.left - tooltipRect.width - 8;
          y = triggerRect.top + (triggerRect.height / 2) - (tooltipRect.height / 2);
          break;
        case 'right':
          x = triggerRect.right + 8;
          y = triggerRect.top + (triggerRect.height / 2) - (tooltipRect.height / 2);
          break;
      }

      // Keep tooltip within viewport
      x = Math.max(8, Math.min(x, window.innerWidth - tooltipRect.width - 8));
      y = Math.max(8, Math.min(y, window.innerHeight - tooltipRect.height - 8));

      setCoords({ x, y });
    }
  }, [isVisible, position]);

  return (
    <>
      <span
        ref={triggerRef}
        className="inline-flex items-center cursor-help"
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
      >
        {children || (
          <svg className="w-3.5 h-3.5 text-muted hover:text-foreground-secondary transition-colors" viewBox="0 0 16 16" fill="currentColor">
            <path fillRule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8zm6.5-.25A.75.75 0 017.25 7h1a.75.75 0 01.75.75v2.75h.25a.75.75 0 010 1.5h-2a.75.75 0 010-1.5h.25v-2h-.25a.75.75 0 01-.75-.75zM8 6a1 1 0 100-2 1 1 0 000 2z" />
          </svg>
        )}
      </span>
      {isVisible && (
        <div
          ref={tooltipRef}
          className="fixed z-[100] px-3 py-2 text-xs leading-relaxed bg-background-elevated text-foreground rounded-lg shadow-lg border border-border max-w-[280px] pointer-events-none"
          style={{ left: coords.x, top: coords.y }}
        >
          {content}
        </div>
      )}
    </>
  );
}

// Predefined glossary tooltips
export const GLOSSARY = {
  scenario: "A PSDL scenario defines a clinical detection rule with signals, logic, and outputs. Each scenario has a unique identifier and version.",
  identifier: "A unique snake_case name for this scenario (e.g., aki_detection, hypoglycemia_alert). Used to reference this scenario in other systems.",
  version: "Semantic version (e.g., 1.0.0) for tracking changes. Increment when modifying the scenario logic.",

  population: "Defines which patients this scenario applies to. Use include/exclude criteria to narrow the target population.",
  includeConditions: "Medical conditions (diagnoses) that patients must have for this scenario to apply. Uses SNOMED-CT codes.",
  includeMedications: "Medications patients must be taking for this scenario to apply. Uses RxNorm codes.",
  excludeConditions: "Conditions that disqualify patients from this scenario (e.g., exclude hospice patients).",
  demographics: "Age and sex filters to further narrow the target population.",

  signals: "Raw clinical data inputs like lab values, vital signs, or measurements. Signals are the foundation of your detection logic.",
  signalRef: "The clinical concept this signal represents (e.g., creatinine, glucose, heart_rate).",

  trends: "Calculated metrics derived from signals over time. Examples: delta (change), rate (velocity), percent_change.",
  delta: "Absolute change in a signal value over a time window (e.g., creatinine increased by 0.3 mg/dL in 48h).",
  rate: "Speed of change per unit time (e.g., glucose dropping 5 mg/dL per hour).",
  percentChange: "Relative change as a percentage (e.g., 50% increase in creatinine).",

  logicRules: "Named boolean expressions that evaluate clinical conditions. Rules can reference signals, trends, or other rules.",
  ruleName: "Unique identifier for this rule. Use descriptive snake_case names (e.g., aki_stage1, severe_hypoglycemia).",
  severity: "Clinical urgency level: low (informational), medium (needs attention), high (critical/urgent).",
  compositeRule: "A rule that combines other rules using AND/OR logic (e.g., 'aki_stage1 AND bun_rising').",
  whenExpression: "The condition that triggers this rule. Can be a comparison (signal > value) or boolean expression.",

  outputs: "What this scenario exposes to downstream systems like EHR alerts or dashboards.",
  decisions: "Boolean outputs (true/false) based on logic rules. Used to trigger alerts or flag patients.",
  features: "Numeric outputs from trends. Useful for dashboards, scoring systems, or ML features.",

  audit: "Governance metadata for clinical review and regulatory compliance.",
  intent: "The clinical purpose of this scenario. What problem does it solve? Who benefits?",
  rationale: "Evidence or reasoning supporting this detection logic. Cite guidelines or literature.",
  provenance: "Origin and authorship. Who created this? Based on what guidelines or protocols?",
};
