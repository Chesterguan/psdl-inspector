"use client";

import React, { useEffect, useRef, useMemo } from "react";
import mermaid from "mermaid";

interface OutlineData {
  scenario: string;
  version: string | null;
  description?: string | null;
  signals: Array<{
    name: string;
    source: string | null;
    unit?: string | null;
    used_by: string[];
  }>;
  trends: Array<{
    name: string;
    expr: string;
    description?: string | null;
    depends_on: string[];
    used_by: string[];
  }>;
  logic: Array<{
    name: string;
    expr: string;
    severity?: string | null;
    description?: string | null;
    depends_on: string[];
    operators: string[];
  }>;
}

interface DAGViewProps {
  outline: OutlineData | null;
}

// Initialize mermaid with dark theme
mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  themeVariables: {
    primaryColor: "#3b82f6",
    primaryTextColor: "#fff",
    primaryBorderColor: "#60a5fa",
    lineColor: "#9ca3af",
    secondaryColor: "#f59e0b",
    tertiaryColor: "#22c55e",
    background: "#111827",
    mainBkg: "#1f2937",
    nodeBorder: "#4b5563",
    clusterBkg: "#374151",
    titleColor: "#f3f4f6",
    edgeLabelBackground: "#1f2937",
  },
  flowchart: {
    htmlLabels: true,
    curve: "basis",
    nodeSpacing: 50,
    rankSpacing: 70,
  },
});

// Check if any logic has complex expressions (multiple operators)
function hasComplexExpressions(outline: OutlineData): boolean {
  return outline.logic.some((logic) => logic.operators.length > 1);
}

function generateMermaidCode(outline: OutlineData): string {
  const lines: string[] = ["graph TD"];

  // Add subgraph for signals
  lines.push("  subgraph Signals");
  outline.signals.forEach((signal) => {
    const label = signal.unit
      ? `${signal.name}<br/><small>${signal.source || 'unknown'} (${signal.unit})</small>`
      : `${signal.name}<br/><small>${signal.source || 'unknown'}</small>`;
    lines.push(`    ${signal.name}[/"${label}"/]:::signal`);
  });
  lines.push("  end");

  // Add subgraph for trends
  lines.push("  subgraph Trends");
  outline.trends.forEach((trend) => {
    const exprShort = trend.expr.length > 30 ? trend.expr.slice(0, 30) + "..." : trend.expr;
    lines.push(`    ${trend.name}["${trend.name}<br/><small>${exprShort}</small>"]:::trend`);
  });
  lines.push("  end");

  // Add subgraph for logic
  lines.push("  subgraph Logic");
  outline.logic.forEach((logic) => {
    const severity = logic.severity ? `[${logic.severity.toUpperCase()}]` : "";
    // Show the expression in the node for clarity
    const exprDisplay = logic.expr.length > 25 ? logic.expr.slice(0, 25) + "..." : logic.expr;
    lines.push(`    ${logic.name}{{"${logic.name} ${severity}<br/><small>${exprDisplay}</small>"}}:::logic`);
  });
  lines.push("  end");

  // Add edges from signals to trends
  outline.trends.forEach((trend) => {
    trend.depends_on.forEach((dep) => {
      if (outline.signals.some((s) => s.name === dep)) {
        lines.push(`  ${dep} --> ${trend.name}`);
      }
    });
  });

  // Add edges from trends/logic to logic WITH gate nodes for AND/OR
  outline.logic.forEach((logic) => {
    const deps = logic.depends_on;
    const operators = logic.operators || [];

    // Filter to valid dependencies
    const validDeps = deps.filter((dep) => {
      const isTrend = outline.trends.some((t) => t.name === dep);
      const isLogic = outline.logic.some((l) => l.name === dep);
      return isTrend || isLogic;
    });

    if (validDeps.length === 0) return;

    if (validDeps.length === 1) {
      // Single dependency - direct connection
      lines.push(`  ${validDeps[0]} --> ${logic.name}`);
    } else if (operators.length > 0) {
      // Multiple dependencies with operator - create gate node
      const gateId = `gate_${logic.name}`;
      const op = operators[0]; // Primary operator

      // Add gate node (diamond shape for decision)
      lines.push(`  ${gateId}((${op})):::gate`);

      // Connect all dependencies to the gate
      validDeps.forEach((dep) => {
        lines.push(`  ${dep} --> ${gateId}`);
      });

      // Connect gate to logic
      lines.push(`  ${gateId} --> ${logic.name}`);
    } else {
      // Multiple dependencies, no operator - just connect all
      validDeps.forEach((dep) => {
        lines.push(`  ${dep} --> ${logic.name}`);
      });
    }
  });

  // Add styles
  lines.push("  classDef signal fill:#dbeafe,stroke:#3b82f6,stroke-width:2px,color:#1e40af");
  lines.push("  classDef trend fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#92400e");
  lines.push("  classDef logic fill:#dcfce7,stroke:#22c55e,stroke-width:2px,color:#166534");
  lines.push("  classDef gate fill:#e879f9,stroke:#a855f7,stroke-width:3px,color:#581c87,font-weight:bold");

  return lines.join("\n");
}

export function DAGView({ outline }: DAGViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const diagramId = useRef(`mermaid-${Date.now()}`);

  const mermaidCode = useMemo(() => {
    if (!outline) return null;
    return generateMermaidCode(outline);
  }, [outline]);

  const showComplexWarning = useMemo(() => {
    if (!outline) return false;
    return hasComplexExpressions(outline);
  }, [outline]);

  useEffect(() => {
    async function renderDiagram() {
      if (!containerRef.current || !mermaidCode) return;

      try {
        // Clear previous content
        containerRef.current.innerHTML = "";

        // Generate new ID for each render
        diagramId.current = `mermaid-${Date.now()}`;

        // Render the diagram
        const { svg } = await mermaid.render(diagramId.current, mermaidCode);
        containerRef.current.innerHTML = svg;

        // Make SVG responsive
        const svgElement = containerRef.current.querySelector("svg");
        if (svgElement) {
          svgElement.style.maxWidth = "100%";
          svgElement.style.height = "auto";
          svgElement.style.minHeight = "400px";
        }
      } catch (error) {
        console.error("Mermaid render error:", error);
        containerRef.current.innerHTML = `
          <div class="text-red-400 p-4">
            <p>Failed to render diagram</p>
            <pre class="text-xs mt-2 text-gray-500">${error}</pre>
          </div>
        `;
      }
    }

    renderDiagram();
  }, [mermaidCode]);

  if (!outline) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        Validate a scenario to see the DAG visualization
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Warning for complex expressions */}
      {showComplexWarning && (
        <div className="bg-amber-900/50 border-b border-amber-700 px-4 py-2 text-amber-200 text-sm flex items-center gap-2">
          <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span>
            Complex expressions detected. Gate structure may be approximate.
            <a href="https://github.com/Chesterguan/PSDL/issues/6" target="_blank" rel="noopener noreferrer" className="underline ml-1 hover:text-amber-100">
              See psdl-lang RFC #6
            </a>
          </span>
        </div>
      )}

      {/* Diagram */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto p-4 flex items-center justify-center bg-gray-900"
      />

      {/* Legend */}
      <div className="border-t border-gray-700 p-3 bg-gray-800 flex items-center justify-between text-sm">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: "#dbeafe", border: "2px solid #3b82f6" }} />
            <span className="text-gray-300">Signal</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: "#fef3c7", border: "2px solid #f59e0b" }} />
            <span className="text-gray-300">Trend</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full" style={{ background: "#e879f9", border: "2px solid #a855f7" }} />
            <span className="text-gray-300">Gate (AND/OR)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: "#dcfce7", border: "2px solid #22c55e" }} />
            <span className="text-gray-300">Logic</span>
          </div>
        </div>
        <div className="text-gray-500 text-xs">
          Signal → Trend → Gate → Logic
        </div>
      </div>

      {/* Mermaid Code (collapsible for debugging) */}
      <details className="border-t border-gray-700">
        <summary className="p-2 text-xs text-gray-500 cursor-pointer hover:text-gray-300">
          View Mermaid Code
        </summary>
        <pre className="p-3 bg-gray-950 text-xs text-gray-400 overflow-x-auto">
          {mermaidCode}
        </pre>
      </details>
    </div>
  );
}
