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

  // Add edges from trends/logic to logic with operator labels
  outline.logic.forEach((logic) => {
    const deps = logic.depends_on;
    // Use operators from psdl-lang (e.g., ["AND"], ["OR"], ["AND", "OR"])
    const operators = logic.operators || [];
    const operatorLabel = operators.length > 0 ? operators.join(" ") : "";

    deps.forEach((dep) => {
      // Check if this dep is a trend or another logic
      const isTrend = outline.trends.some((t) => t.name === dep);
      const isLogic = outline.logic.some((l) => l.name === dep);

      if (isTrend || isLogic) {
        if (operatorLabel && deps.length > 1) {
          lines.push(`  ${dep} -->|${operatorLabel}| ${logic.name}`);
        } else {
          lines.push(`  ${dep} --> ${logic.name}`);
        }
      }
    });
  });

  // Add styles
  lines.push("  classDef signal fill:#dbeafe,stroke:#3b82f6,stroke-width:2px,color:#1e40af");
  lines.push("  classDef trend fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#92400e");
  lines.push("  classDef logic fill:#dcfce7,stroke:#22c55e,stroke-width:2px,color:#166534");

  return lines.join("\n");
}

export function DAGView({ outline }: DAGViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const diagramId = useRef(`mermaid-${Date.now()}`);

  const mermaidCode = useMemo(() => {
    if (!outline) return null;
    return generateMermaidCode(outline);
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
      {/* Diagram */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto p-4 flex items-center justify-center bg-gray-900"
      />

      {/* Legend */}
      <div className="border-t border-gray-700 p-3 bg-gray-800 flex items-center justify-between text-sm">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: "#dbeafe", border: "2px solid #3b82f6" }} />
            <span className="text-gray-300">Signal (data input)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: "#fef3c7", border: "2px solid #f59e0b" }} />
            <span className="text-gray-300">Trend (computation)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: "#dcfce7", border: "2px solid #22c55e" }} />
            <span className="text-gray-300">Logic (decision)</span>
          </div>
        </div>
        <div className="text-gray-500">
          AND/OR labels show boolean operators
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
