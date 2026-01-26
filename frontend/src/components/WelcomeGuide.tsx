'use client';

import { useState, useEffect } from 'react';
import { X, Sparkles, FileCode, Eye, Download, ArrowRight, HelpCircle, Lightbulb, AlertTriangle } from 'lucide-react';

interface WelcomeGuideProps {
  onClose: () => void;
  isOpen: boolean;
}

const STEPS = [
  {
    icon: Sparkles,
    title: 'Generate or Write',
    description: 'Create scenarios using AI assistance or write YAML manually',
    details: [
      'Generate: Describe your clinical scenario in plain language',
      'Build: Use the visual builder to construct scenarios step-by-step',
      'Edit: Write or paste YAML directly with syntax highlighting'
    ],
    color: 'text-accent-purple'
  },
  {
    icon: Eye,
    title: 'Preview & Validate',
    description: 'Visualize your scenario structure and verify correctness',
    details: [
      'Outline: See signals, trends, and logic in a tree view',
      'DAG: Interactive graph showing data flow dependencies',
      'Validation: Real-time syntax and semantic checks via psdl-lang'
    ],
    color: 'text-accent-cyan'
  },
  {
    icon: Download,
    title: 'Export & Certify',
    description: 'Generate audit-ready bundles and documentation',
    details: [
      'JSON Bundle: Checksummed certified bundle for systems integration',
      'Word Document: AI-enriched IRB documentation',
      'Governance metadata: Intent, rationale, and provenance tracking'
    ],
    color: 'text-accent-success'
  }
];

const QUICK_TIPS = [
  {
    icon: Lightbulb,
    tip: 'PSDL uses: signals (inputs) → trends (computed values) → logic (rules)',
    color: 'text-yellow-500'
  },
  {
    icon: AlertTriangle,
    tip: 'Logic expressions must reference trends, not signals directly',
    color: 'text-orange-500'
  },
  {
    icon: FileCode,
    tip: 'Use "Insert Template" in the editor for a starter skeleton',
    color: 'text-accent-cyan'
  }
];

export default function WelcomeGuide({ onClose, isOpen }: WelcomeGuideProps) {
  const [currentStep, setCurrentStep] = useState(0);

  // Reset to first step when opened
  useEffect(() => {
    if (isOpen) setCurrentStep(0);
  }, [isOpen]);

  if (!isOpen) return null;

  const isLastStep = currentStep === STEPS.length - 1;

  return (
    <div className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-background rounded-2xl shadow-2xl border border-border max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-background-secondary">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-purple to-accent-cyan flex items-center justify-center">
              <HelpCircle className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-foreground">Welcome to PSDL Inspector</h2>
              <p className="text-sm text-muted">Governance middleware for clinical scenarios</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-background-tertiary rounded-lg transition-colors text-muted hover:text-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Step Progress */}
          <div className="flex items-center justify-center gap-2 mb-6">
            {STEPS.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentStep(idx)}
                className={`w-3 h-3 rounded-full transition-all ${
                  idx === currentStep
                    ? 'bg-accent scale-125'
                    : idx < currentStep
                      ? 'bg-accent/50'
                      : 'bg-border hover:bg-muted'
                }`}
              />
            ))}
          </div>

          {/* Current Step */}
          <div className="text-center mb-8">
            <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-background-secondary mb-4 ${STEPS[currentStep].color}`}>
              {(() => {
                const Icon = STEPS[currentStep].icon;
                return <Icon className="w-8 h-8" />;
              })()}
            </div>
            <h3 className="text-xl font-bold text-foreground mb-2">
              Step {currentStep + 1}: {STEPS[currentStep].title}
            </h3>
            <p className="text-foreground-secondary mb-4">
              {STEPS[currentStep].description}
            </p>
            <ul className="text-left max-w-md mx-auto space-y-2">
              {STEPS[currentStep].details.map((detail, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-foreground-secondary">
                  <ArrowRight className="w-4 h-4 mt-0.5 text-accent flex-shrink-0" />
                  <span>{detail}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Quick Tips (shown on last step) */}
          {isLastStep && (
            <div className="bg-background-secondary rounded-xl p-4 mb-4">
              <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-yellow-500" />
                Quick Tips
              </h4>
              <div className="space-y-2">
                {QUICK_TIPS.map((item, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-sm">
                    <item.icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${item.color}`} />
                    <span className="text-foreground-secondary">{item.tip}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* PSDL Structure Overview (shown on first step) */}
          {currentStep === 0 && (
            <div className="bg-background-secondary rounded-xl p-4 font-mono text-xs">
              <div className="text-muted mb-2"># PSDL Structure</div>
              <div className="space-y-1">
                <div><span className="text-accent-purple">scenario:</span> <span className="text-foreground-secondary">name_of_scenario</span></div>
                <div><span className="text-accent-purple">signals:</span> <span className="text-muted"># Data inputs (heart_rate, blood_pressure, etc.)</span></div>
                <div><span className="text-accent-purple">trends:</span> <span className="text-muted"># Computed values (avg, delta, min, max)</span></div>
                <div><span className="text-accent-purple">logic:</span> <span className="text-muted"># Decision rules with severity levels</span></div>
                <div><span className="text-accent-purple">outputs:</span> <span className="text-muted"># What to expose downstream</span></div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-background-secondary">
          <button
            onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
            disabled={currentStep === 0}
            className="px-4 py-2 text-sm font-medium text-foreground-secondary hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Back
          </button>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-foreground-secondary hover:text-foreground transition-colors"
            >
              Skip
            </button>
            {isLastStep ? (
              <button
                onClick={onClose}
                className="px-5 py-2 text-sm font-medium bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors"
              >
                Get Started
              </button>
            ) : (
              <button
                onClick={() => setCurrentStep(currentStep + 1)}
                className="px-5 py-2 text-sm font-medium bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors flex items-center gap-2"
              >
                Next
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Hook to manage welcome guide visibility
export function useWelcomeGuide() {
  const [isOpen, setIsOpen] = useState(false);
  const [hasSeenGuide, setHasSeenGuide] = useState(true); // Default true to prevent flash

  useEffect(() => {
    // Check localStorage on mount
    const seen = localStorage.getItem('psdl-inspector-welcome-seen');
    if (!seen) {
      setIsOpen(true);
      setHasSeenGuide(false);
    }
  }, []);

  const closeGuide = () => {
    setIsOpen(false);
    localStorage.setItem('psdl-inspector-welcome-seen', 'true');
    setHasSeenGuide(true);
  };

  const openGuide = () => {
    setIsOpen(true);
  };

  return { isOpen, hasSeenGuide, closeGuide, openGuide };
}
