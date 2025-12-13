'use client';

import { useState } from 'react';
import { ChevronRight, ChevronDown, Zap, TrendingUp, GitBranch } from 'lucide-react';
import type { OutlineResponse, SignalOutline, TrendOutline, LogicOutline } from '@/lib/api';

interface OutlineTreeProps {
  outline: OutlineResponse | null;
  isLoading: boolean;
}

interface TreeSectionProps {
  title: string;
  icon: React.ReactNode;
  count: number;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

function TreeSection({ title, icon, count, children, defaultOpen = true }: TreeSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="mb-4">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 w-full text-left hover:bg-gray-800 p-2 rounded"
      >
        {isOpen ? (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-500" />
        )}
        {icon}
        <span className="font-medium">{title}</span>
        <span className="text-gray-500 text-sm">({count})</span>
      </button>
      {isOpen && <div className="ml-6 mt-1 space-y-1">{children}</div>}
    </div>
  );
}

function SignalItem({ signal }: { signal: SignalOutline }) {
  return (
    <div className="p-2 rounded bg-gray-800/50 hover:bg-gray-800">
      <div className="flex items-center gap-2">
        <span className="font-mono text-blue-400">{signal.name}</span>
        {signal.unit && (
          <span className="text-xs text-gray-500">({signal.unit})</span>
        )}
      </div>
      <div className="text-xs text-gray-500 mt-1">
        source: {signal.source || 'N/A'}
        {signal.concept_id && ` | concept: ${signal.concept_id}`}
      </div>
      {signal.used_by.length > 0 && (
        <div className="text-xs text-gray-600 mt-1">
          Used by: {signal.used_by.join(', ')}
        </div>
      )}
    </div>
  );
}

function TrendItem({ trend }: { trend: TrendOutline }) {
  return (
    <div className="p-2 rounded bg-gray-800/50 hover:bg-gray-800">
      <div className="flex items-center gap-2">
        <span className="font-mono text-purple-400">{trend.name}</span>
      </div>
      <div className="text-xs font-mono text-gray-400 mt-1 bg-gray-900 p-1 rounded">
        {trend.expr}
      </div>
      {trend.description && (
        <div className="text-xs text-gray-500 mt-1">{trend.description}</div>
      )}
      <div className="text-xs text-gray-600 mt-1">
        {trend.depends_on.length > 0 && (
          <span>Signals: {trend.depends_on.join(', ')}</span>
        )}
        {trend.used_by.length > 0 && (
          <span className="ml-2">| Used by: {trend.used_by.join(', ')}</span>
        )}
      </div>
    </div>
  );
}

function LogicItem({ logic }: { logic: LogicOutline }) {
  const severityColors: Record<string, string> = {
    low: 'text-green-400',
    medium: 'text-yellow-400',
    high: 'text-orange-400',
    critical: 'text-red-400',
  };

  return (
    <div className="p-2 rounded bg-gray-800/50 hover:bg-gray-800">
      <div className="flex items-center gap-2">
        <span className="font-mono text-green-400">{logic.name}</span>
        {logic.severity && (
          <span
            className={`text-xs px-1.5 py-0.5 rounded ${severityColors[logic.severity] || 'text-gray-400'} bg-gray-900`}
          >
            {logic.severity.toUpperCase()}
          </span>
        )}
      </div>
      <div className="text-xs font-mono text-gray-400 mt-1 bg-gray-900 p-1 rounded">
        {logic.expr}
      </div>
      {logic.description && (
        <div className="text-xs text-gray-500 mt-1">{logic.description}</div>
      )}
      {logic.depends_on.length > 0 && (
        <div className="text-xs text-gray-600 mt-1">
          Depends on: {logic.depends_on.join(', ')}
        </div>
      )}
    </div>
  );
}

export default function OutlineTree({ outline, isLoading }: OutlineTreeProps) {
  if (isLoading) {
    return (
      <div className="p-4 text-gray-400 text-sm">
        Generating outline...
      </div>
    );
  }

  if (!outline) {
    return (
      <div className="p-4 text-gray-500 text-sm">
        No outline available. Validate a scenario first.
      </div>
    );
  }

  return (
    <div className="p-4">
      {/* Header */}
      <div className="mb-4 pb-3 border-b border-gray-700">
        <h2 className="text-lg font-bold">{outline.scenario}</h2>
        {outline.version && (
          <span className="text-sm text-gray-500">v{outline.version}</span>
        )}
        {outline.description && (
          <p className="text-sm text-gray-400 mt-1">{outline.description}</p>
        )}
      </div>

      {/* Signals */}
      <TreeSection
        title="Signals"
        icon={<Zap className="w-4 h-4 text-blue-400" />}
        count={outline.signals.length}
      >
        {outline.signals.map((signal) => (
          <SignalItem key={signal.name} signal={signal} />
        ))}
      </TreeSection>

      {/* Trends */}
      <TreeSection
        title="Trends"
        icon={<TrendingUp className="w-4 h-4 text-purple-400" />}
        count={outline.trends.length}
      >
        {outline.trends.map((trend) => (
          <TrendItem key={trend.name} trend={trend} />
        ))}
      </TreeSection>

      {/* Logic */}
      <TreeSection
        title="Logic"
        icon={<GitBranch className="w-4 h-4 text-green-400" />}
        count={outline.logic.length}
      >
        {outline.logic.map((logic) => (
          <LogicItem key={logic.name} logic={logic} />
        ))}
      </TreeSection>
    </div>
  );
}
