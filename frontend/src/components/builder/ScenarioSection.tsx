'use client';

import Tooltip, { GLOSSARY } from './Tooltip';

interface ScenarioSectionProps {
  scenario: {
    name: string;
    description: string;
    version: string;
  };
  onChange: (field: string, value: string) => void;
}

export default function ScenarioSection({ scenario, onChange }: ScenarioSectionProps) {
  return (
    <div className="section-panel bg-background-secondary rounded-lg">
      <div className="section-header flex items-center gap-3 px-4 py-3 bg-background-tertiary rounded-t-lg">
        <span className="section-number w-7 h-7 flex items-center justify-center bg-accent-cyan/20 rounded font-mono text-sm font-bold text-accent-cyan">01</span>
        <span className="section-title text-sm font-semibold text-foreground">Scenario Definition</span>
        <Tooltip content={GLOSSARY.scenario} />
      </div>
      <div className="section-body px-4 py-4 space-y-4">
        <div className="form-group">
          <div className="flex items-center gap-1.5 mb-2">
            <label className="form-label text-sm font-semibold text-foreground-secondary">Identifier</label>
            <Tooltip content={GLOSSARY.identifier} />
          </div>
          <input
            type="text"
            className="form-input w-full px-3 py-2.5 bg-background rounded-md text-foreground font-mono text-sm focus:ring-2 focus:ring-accent/30 outline-none transition-all placeholder:text-muted/50"
            placeholder="hypoglycemia_alert"
            value={scenario.name}
            onChange={(e) => onChange('name', e.target.value)}
          />
        </div>
        <div className="form-group">
          <label className="form-label block text-sm font-semibold text-foreground-secondary mb-2">Description</label>
          <textarea
            className="form-textarea w-full px-3 py-2.5 bg-background rounded-md text-foreground text-sm min-h-[60px] resize-y focus:ring-2 focus:ring-accent/30 outline-none transition-all placeholder:text-muted/50"
            placeholder="Clinical scenario description..."
            value={scenario.description}
            onChange={(e) => onChange('description', e.target.value)}
          />
        </div>
        <div className="form-group">
          <div className="flex items-center gap-1.5 mb-2">
            <label className="form-label text-sm font-semibold text-foreground-secondary">Version</label>
            <Tooltip content={GLOSSARY.version} />
          </div>
          <input
            type="text"
            className="form-input w-full px-3 py-2.5 bg-background rounded-md text-foreground font-mono text-sm focus:ring-2 focus:ring-accent/30 outline-none transition-all"
            value={scenario.version}
            onChange={(e) => onChange('version', e.target.value)}
          />
        </div>
      </div>
    </div>
  );
}
