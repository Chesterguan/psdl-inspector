"use client";

import React, { useMemo, useState, useCallback } from "react";
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  MarkerType,
  NodeMouseHandler,
} from "@xyflow/react";
import dagre from "dagre";
import "@xyflow/react/dist/style.css";
import { useTheme } from "@/context/ThemeContext";

// =============================================================================
// Types
// =============================================================================

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

// =============================================================================
// Custom Node Components (without tooltips)
// =============================================================================

interface NodeData {
  label: string;
  sublabel?: string;
  expr?: string;
  severity?: string;
  description?: string;
  nodeType?: string;
}

// Signal Node - Parallelogram shape (input)
function SignalNode({ data }: { data: NodeData }) {
  return (
    <div className="relative cursor-pointer">
      <div
        className="px-4 py-2 min-w-[120px] text-center rounded-lg border-2 transition-all duration-200
                   bg-gradient-to-br from-blue-500/20 to-blue-600/30 border-blue-400
                   hover:border-blue-300 hover:shadow-lg hover:shadow-blue-500/20"
        style={{ transform: "skewX(-6deg)" }}
      >
        <div style={{ transform: "skewX(6deg)" }}>
          <div className="font-semibold text-blue-800 dark:text-blue-100">{data.label}</div>
          {data.sublabel && (
            <div className="text-xs text-blue-600 dark:text-blue-300/80 mt-0.5">{data.sublabel}</div>
          )}
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2 h-2 !bg-blue-400 !border-blue-300"
      />
    </div>
  );
}

// Trend Node - Rounded rectangle (computation)
function TrendNode({ data }: { data: NodeData }) {
  return (
    <div className="relative cursor-pointer">
      <Handle
        type="target"
        position={Position.Top}
        className="w-2 h-2 !bg-amber-400 !border-amber-300"
      />
      <div
        className="px-4 py-2 min-w-[140px] text-center rounded-xl border-2 transition-all duration-200
                   bg-gradient-to-br from-amber-500/20 to-orange-600/30 border-amber-400
                   hover:border-amber-300 hover:shadow-lg hover:shadow-amber-500/20"
      >
        <div className="font-semibold text-amber-800 dark:text-amber-100">{data.label}</div>
        {data.expr && (
          <div className="text-xs text-amber-600 dark:text-amber-300/80 mt-0.5 font-mono max-w-[160px] truncate">
            {data.expr}
          </div>
        )}
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2 h-2 !bg-amber-400 !border-amber-300"
      />
    </div>
  );
}

// Gate Node - Diamond shape (AND/OR)
function GateNode({ data }: { data: NodeData }) {
  return (
    <div className="relative cursor-pointer">
      <Handle
        type="target"
        position={Position.Top}
        className="w-2 h-2 !bg-purple-400 !border-purple-300"
      />
      <div
        className="w-12 h-12 flex items-center justify-center border-2 transition-all duration-200
                   bg-gradient-to-br from-purple-500/30 to-pink-600/30 border-purple-400
                   hover:border-purple-300 hover:shadow-lg hover:shadow-purple-500/20"
        style={{ transform: "rotate(45deg)", borderRadius: "4px" }}
      >
        <span
          className="font-bold text-purple-800 dark:text-purple-100 text-sm"
          style={{ transform: "rotate(-45deg)" }}
        >
          {data.label}
        </span>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2 h-2 !bg-purple-400 !border-purple-300"
      />
    </div>
  );
}

// Logic Node - Hexagon shape (decision)
function LogicNode({ data }: { data: NodeData }) {
  const severityColors: Record<string, string> = {
    low: "from-green-500/20 to-emerald-600/30 border-green-400 hover:border-green-300 hover:shadow-green-500/20",
    medium: "from-yellow-500/20 to-amber-600/30 border-yellow-400 hover:border-yellow-300 hover:shadow-yellow-500/20",
    high: "from-orange-500/20 to-red-600/30 border-orange-400 hover:border-orange-300 hover:shadow-orange-500/20",
    critical: "from-red-500/20 to-rose-600/30 border-red-400 hover:border-red-300 hover:shadow-red-500/20",
  };

  const severityBadgeColors: Record<string, string> = {
    low: "bg-green-500/30 text-green-700 dark:text-green-300",
    medium: "bg-yellow-500/30 text-yellow-700 dark:text-yellow-300",
    high: "bg-orange-500/30 text-orange-700 dark:text-orange-300",
    critical: "bg-red-500/30 text-red-700 dark:text-red-300",
  };

  const colorClass = data.severity ? severityColors[data.severity] || severityColors.medium : severityColors.medium;
  const badgeClass = data.severity ? severityBadgeColors[data.severity] || "" : "";

  return (
    <div className="relative cursor-pointer">
      <Handle
        type="target"
        position={Position.Top}
        className="w-2 h-2 !bg-green-400 !border-green-300"
      />
      <div
        className={`px-4 py-2 min-w-[140px] text-center border-2 transition-all duration-200
                   bg-gradient-to-br ${colorClass}`}
        style={{
          clipPath: "polygon(10% 0%, 90% 0%, 100% 50%, 90% 100%, 10% 100%, 0% 50%)",
          padding: "12px 20px",
        }}
      >
        <div className="font-semibold text-foreground">{data.label}</div>
        {data.severity && (
          <div className={`text-xs mt-0.5 px-2 py-0.5 rounded-full inline-block ${badgeClass}`}>
            {data.severity.toUpperCase()}
          </div>
        )}
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2 h-2 !bg-green-400 !border-green-300"
      />
    </div>
  );
}

// Node types registry
const nodeTypes = {
  signal: SignalNode,
  trend: TrendNode,
  gate: GateNode,
  logic: LogicNode,
};

// =============================================================================
// Layout with Dagre
// =============================================================================

const NODE_WIDTH = 150;
const NODE_HEIGHT = 60;

function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction = "TB"
): { nodes: Node[]; edges: Edge[] } {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction, nodesep: 60, ranksep: 80 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

// =============================================================================
// Build Graph from Outline
// =============================================================================

function buildGraph(outline: OutlineData): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  // Add signal nodes
  outline.signals.forEach((signal) => {
    const id = `signal-${signal.name}`;
    nodes.push({
      id,
      type: "signal",
      position: { x: 0, y: 0 },
      data: {
        label: signal.name,
        sublabel: signal.unit ? `${signal.source || "ref"} (${signal.unit})` : signal.source || "ref",
        description: `Signal: ${signal.name}`,
        nodeType: "signal",
      },
    });
  });

  // Add trend nodes
  outline.trends.forEach((trend) => {
    const id = `trend-${trend.name}`;
    nodes.push({
      id,
      type: "trend",
      position: { x: 0, y: 0 },
      data: {
        label: trend.name,
        expr: trend.expr,
        description: trend.description || undefined,
        nodeType: "trend",
      },
    });

    // Add edges from dependencies
    trend.depends_on.forEach((dep) => {
      const sourceId = outline.signals.some((s) => s.name === dep)
        ? `signal-${dep}`
        : `trend-${dep}`;
      edges.push({
        id: `edge-${sourceId}-${id}`,
        source: sourceId,
        target: id,
        animated: false,
        style: { stroke: "#9ca3af", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#9ca3af" },
      });
    });
  });

  // Add logic nodes with gates
  outline.logic.forEach((logic) => {
    const logicId = `logic-${logic.name}`;

    // Filter valid dependencies
    const validDeps = logic.depends_on.filter((dep) => {
      const isTrend = outline.trends.some((t) => t.name === dep);
      const isLogic = outline.logic.some((l) => l.name === dep);
      const isSignal = outline.signals.some((s) => s.name === dep);
      return isTrend || isLogic || isSignal;
    });

    nodes.push({
      id: logicId,
      type: "logic",
      position: { x: 0, y: 0 },
      data: {
        label: logic.name,
        expr: logic.expr,
        severity: logic.severity || undefined,
        description: logic.description || undefined,
        nodeType: "logic",
      },
    });

    // If multiple dependencies and has operator, add gate node
    if (validDeps.length > 1 && logic.operators.length > 0) {
      const gateId = `gate-${logic.name}`;
      const op = logic.operators[0];

      nodes.push({
        id: gateId,
        type: "gate",
        position: { x: 0, y: 0 },
        data: { label: op, nodeType: "gate" },
      });

      // Connect deps to gate
      validDeps.forEach((dep) => {
        const sourceId = outline.signals.some((s) => s.name === dep)
          ? `signal-${dep}`
          : outline.trends.some((t) => t.name === dep)
          ? `trend-${dep}`
          : `logic-${dep}`;

        edges.push({
          id: `edge-${sourceId}-${gateId}`,
          source: sourceId,
          target: gateId,
          animated: false,
          style: { stroke: "#a78bfa", strokeWidth: 2 },
          markerEnd: { type: MarkerType.ArrowClosed, color: "#a78bfa" },
        });
      });

      // Connect gate to logic
      edges.push({
        id: `edge-${gateId}-${logicId}`,
        source: gateId,
        target: logicId,
        animated: true,
        style: { stroke: "#22c55e", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#22c55e" },
      });
    } else {
      // Direct connections
      validDeps.forEach((dep) => {
        const sourceId = outline.signals.some((s) => s.name === dep)
          ? `signal-${dep}`
          : outline.trends.some((t) => t.name === dep)
          ? `trend-${dep}`
          : `logic-${dep}`;

        edges.push({
          id: `edge-${sourceId}-${logicId}`,
          source: sourceId,
          target: logicId,
          animated: false,
          style: { stroke: "#22c55e", strokeWidth: 2 },
          markerEnd: { type: MarkerType.ArrowClosed, color: "#22c55e" },
        });
      });
    }
  });

  return getLayoutedElements(nodes, edges);
}

// =============================================================================
// Details Panel Component
// =============================================================================

interface DetailsPanelProps {
  node: Node | null;
}

function DetailsPanel({ node }: DetailsPanelProps) {
  if (!node) {
    return (
      <div className="text-muted text-sm text-center py-4">
        Hover over a node to see details
      </div>
    );
  }

  const data = node.data as unknown as NodeData;
  const nodeType = data.nodeType || node.type;

  const typeColors: Record<string, { bg: string; text: string; border: string }> = {
    signal: { bg: "bg-blue-100 dark:bg-blue-900/30", text: "text-blue-700 dark:text-blue-300", border: "border-blue-300 dark:border-blue-700" },
    trend: { bg: "bg-amber-100 dark:bg-amber-900/30", text: "text-amber-700 dark:text-amber-300", border: "border-amber-300 dark:border-amber-700" },
    gate: { bg: "bg-purple-100 dark:bg-purple-900/30", text: "text-purple-700 dark:text-purple-300", border: "border-purple-300 dark:border-purple-700" },
    logic: { bg: "bg-green-100 dark:bg-green-900/30", text: "text-green-700 dark:text-green-300", border: "border-green-300 dark:border-green-700" },
  };

  const colors = typeColors[nodeType || "signal"] || typeColors.signal;

  return (
    <div className={`rounded-lg p-3 border ${colors.bg} ${colors.border}`}>
      <div className="flex items-center justify-between mb-2">
        <span className={`font-semibold ${colors.text}`}>{data.label}</span>
        <span className={`text-xs px-2 py-0.5 rounded ${colors.bg} ${colors.text} uppercase`}>
          {nodeType}
        </span>
      </div>

      {data.sublabel && (
        <div className="text-sm text-muted mb-2">
          <span className="text-foreground/70">Source:</span> {data.sublabel}
        </div>
      )}

      {data.expr && (
        <div className="mb-2">
          <div className="text-xs text-muted uppercase mb-1">Expression</div>
          <code className="text-xs font-mono bg-surface px-2 py-1 rounded block overflow-x-auto text-foreground">
            {data.expr}
          </code>
        </div>
      )}

      {data.severity && (
        <div className="mb-2">
          <span className="text-xs text-muted uppercase">Severity: </span>
          <span className={`text-xs font-semibold uppercase ${
            data.severity === "critical" ? "text-red-600 dark:text-red-400" :
            data.severity === "high" ? "text-orange-600 dark:text-orange-400" :
            data.severity === "medium" ? "text-yellow-600 dark:text-yellow-400" :
            "text-green-600 dark:text-green-400"
          }`}>
            {data.severity}
          </span>
        </div>
      )}

      {data.description && (
        <div>
          <div className="text-xs text-muted uppercase mb-1">Description</div>
          <p className="text-sm text-foreground">{data.description}</p>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function DAGView({ outline }: DAGViewProps) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const [hoveredNode, setHoveredNode] = useState<Node | null>(null);

  // Generate a stable key based on outline content
  const flowKey = useMemo(() => {
    if (!outline) return "empty";
    const signalNames = outline.signals.map(s => s.name).join(",");
    const trendNames = outline.trends.map(t => t.name).join(",");
    const logicNames = outline.logic.map(l => l.name).join(",");
    return `${outline.scenario}-${signalNames}-${trendNames}-${logicNames}`;
  }, [outline]);

  const { layoutedNodes, layoutedEdges } = useMemo(() => {
    if (!outline) return { layoutedNodes: [], layoutedEdges: [] };
    const { nodes, edges } = buildGraph(outline);
    return { layoutedNodes: nodes, layoutedEdges: edges };
  }, [outline]);

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);

  // Update when outline changes
  React.useEffect(() => {
    if (outline) {
      const { nodes: newNodes, edges: newEdges } = buildGraph(outline);
      setNodes(newNodes);
      setEdges(newEdges);
    } else {
      setNodes([]);
      setEdges([]);
    }
  }, [outline, setNodes, setEdges]);

  const onNodeMouseEnter: NodeMouseHandler = useCallback((event, node) => {
    setHoveredNode(node);
  }, []);

  const onNodeMouseLeave: NodeMouseHandler = useCallback(() => {
    setHoveredNode(null);
  }, []);

  if (!outline) {
    return (
      <div className="h-full w-full flex items-center justify-center bg-surface/30" style={{ minHeight: '400px' }}>
        <div className="text-center">
          <svg className="w-16 h-16 mx-auto mb-4 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
          </svg>
          <p className="text-slate-500 dark:text-slate-400">Validate a scenario to see the DAG visualization</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col">
      <div className="flex-1 flex" style={{ minHeight: "400px" }}>
        {/* DAG Graph */}
        <div className="flex-1" style={{ width: "100%", height: "100%" }}>
          <ReactFlow
            key={flowKey}
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            onNodeMouseEnter={onNodeMouseEnter}
            onNodeMouseLeave={onNodeMouseLeave}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.3}
            maxZoom={2}
            defaultEdgeOptions={{
              type: "smoothstep",
            }}
            style={{ width: "100%", height: "100%" }}
          >
            <Background color={isDark ? "#374151" : "#d1d5db"} gap={20} size={1} />
            <Controls
              className="!bg-surface !border-border !shadow-lg"
              showInteractive={false}
            />
            <MiniMap
              className="!bg-surface !border-border"
              nodeColor={(node) => {
                switch (node.type) {
                  case "signal": return "#3b82f6";
                  case "trend": return "#f59e0b";
                  case "gate": return "#a855f7";
                  case "logic": return "#22c55e";
                  default: return "#6b7280";
                }
              }}
              maskColor={isDark ? "rgba(0, 0, 0, 0.6)" : "rgba(255, 255, 255, 0.6)"}
            />
          </ReactFlow>
        </div>

        {/* Details Panel - Fixed position on the right */}
        <div className="w-72 border-l border-border bg-surface p-3 overflow-auto flex-shrink-0">
          <h4 className="text-sm font-semibold mb-3 text-foreground">Node Details</h4>
          <DetailsPanel node={hoveredNode} />
        </div>
      </div>

      {/* Legend */}
      <div className="border-t border-border p-3 bg-surface flex items-center justify-between text-sm flex-shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-5 h-4 rounded bg-gradient-to-br from-blue-500/40 to-blue-600/50 border border-blue-400"
                 style={{ transform: "skewX(-6deg)" }} />
            <span className="text-foreground">Signal</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-5 h-4 rounded-lg bg-gradient-to-br from-amber-500/40 to-orange-600/50 border border-amber-400" />
            <span className="text-foreground">Trend</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-gradient-to-br from-purple-500/40 to-pink-600/50 border border-purple-400"
                 style={{ transform: "rotate(45deg)", borderRadius: "2px" }} />
            <span className="text-foreground">Gate</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-5 h-4 bg-gradient-to-br from-green-500/40 to-emerald-600/50 border border-green-400"
                 style={{ clipPath: "polygon(15% 0%, 85% 0%, 100% 50%, 85% 100%, 15% 100%, 0% 50%)" }} />
            <span className="text-foreground">Logic</span>
          </div>
        </div>
        <div className="text-muted text-xs">
          Hover nodes for details
        </div>
      </div>
    </div>
  );
}
