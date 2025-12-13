"use client";

import React, { useMemo } from "react";
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
} from "reactflow";
import dagre from "dagre";
import "reactflow/dist/style.css";

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
  }>;
}

interface DAGViewProps {
  outline: OutlineData | null;
}

// Node dimensions for layout
const NODE_WIDTH = 180;
const NODE_HEIGHT = 60;

// Custom node colors by type
const NODE_COLORS = {
  signal: { bg: "#dbeafe", border: "#3b82f6", text: "#1e40af" },
  trend: { bg: "#fef3c7", border: "#f59e0b", text: "#92400e" },
  logic: { bg: "#dcfce7", border: "#22c55e", text: "#166534" },
};

// Severity colors for logic nodes
const SEVERITY_COLORS: Record<string, string> = {
  low: "#22c55e",
  medium: "#f59e0b",
  high: "#ef4444",
  critical: "#991b1b",
};

function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction = "TB"
): { nodes: Node[]; edges: Edge[] } {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const isHorizontal = direction === "LR";
  dagreGraph.setGraph({ rankdir: direction, nodesep: 50, ranksep: 80 });

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
      targetPosition: isHorizontal ? Position.Left : Position.Top,
      sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

function buildNodesAndEdges(outline: OutlineData): {
  nodes: Node[];
  edges: Edge[];
} {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  // Add signal nodes
  outline.signals.forEach((signal) => {
    nodes.push({
      id: `signal-${signal.name}`,
      type: "default",
      data: {
        label: (
          <div className="text-center">
            <div className="text-xs text-blue-600 font-semibold">SIGNAL</div>
            <div className="font-bold">{signal.name}</div>
            <div className="text-xs text-gray-500">{signal.source || 'unknown'}</div>
          </div>
        ),
      },
      position: { x: 0, y: 0 },
      style: {
        background: NODE_COLORS.signal.bg,
        border: `2px solid ${NODE_COLORS.signal.border}`,
        borderRadius: "8px",
        padding: "8px",
        width: NODE_WIDTH,
      },
    });
  });

  // Add trend nodes
  outline.trends.forEach((trend) => {
    nodes.push({
      id: `trend-${trend.name}`,
      type: "default",
      data: {
        label: (
          <div className="text-center">
            <div className="text-xs text-amber-600 font-semibold">TREND</div>
            <div className="font-bold">{trend.name}</div>
            <div className="text-xs text-gray-500 truncate" title={trend.expr}>
              {trend.expr.length > 25 ? trend.expr.slice(0, 25) + "..." : trend.expr}
            </div>
          </div>
        ),
      },
      position: { x: 0, y: 0 },
      style: {
        background: NODE_COLORS.trend.bg,
        border: `2px solid ${NODE_COLORS.trend.border}`,
        borderRadius: "8px",
        padding: "8px",
        width: NODE_WIDTH,
      },
    });

    // Edges from signals to trends
    trend.depends_on.forEach((dep) => {
      // Check if dependency is a signal
      if (outline.signals.some((s) => s.name === dep)) {
        edges.push({
          id: `signal-${dep}-to-trend-${trend.name}`,
          source: `signal-${dep}`,
          target: `trend-${trend.name}`,
          animated: false,
          style: { stroke: NODE_COLORS.signal.border },
          markerEnd: { type: MarkerType.ArrowClosed },
        });
      }
    });
  });

  // Add logic nodes
  outline.logic.forEach((logic) => {
    const severityColor = logic.severity
      ? SEVERITY_COLORS[logic.severity] || NODE_COLORS.logic.border
      : NODE_COLORS.logic.border;

    nodes.push({
      id: `logic-${logic.name}`,
      type: "default",
      data: {
        label: (
          <div className="text-center">
            <div className="text-xs text-green-600 font-semibold">
              LOGIC {logic.severity && `[${logic.severity.toUpperCase()}]`}
            </div>
            <div className="font-bold">{logic.name}</div>
            <div className="text-xs text-gray-500 truncate" title={logic.expr}>
              {logic.expr.length > 25 ? logic.expr.slice(0, 25) + "..." : logic.expr}
            </div>
          </div>
        ),
      },
      position: { x: 0, y: 0 },
      style: {
        background: NODE_COLORS.logic.bg,
        border: `2px solid ${severityColor}`,
        borderRadius: "8px",
        padding: "8px",
        width: NODE_WIDTH,
      },
    });

    // Edges from trends to logic
    logic.depends_on.forEach((dep) => {
      // Check if dependency is a trend
      if (outline.trends.some((t) => t.name === dep)) {
        edges.push({
          id: `trend-${dep}-to-logic-${logic.name}`,
          source: `trend-${dep}`,
          target: `logic-${logic.name}`,
          animated: false,
          style: { stroke: NODE_COLORS.trend.border },
          markerEnd: { type: MarkerType.ArrowClosed },
        });
      }
      // Check if dependency is another logic (for complex logic)
      if (outline.logic.some((l) => l.name === dep)) {
        edges.push({
          id: `logic-${dep}-to-logic-${logic.name}`,
          source: `logic-${dep}`,
          target: `logic-${logic.name}`,
          animated: false,
          style: { stroke: NODE_COLORS.logic.border },
          markerEnd: { type: MarkerType.ArrowClosed },
        });
      }
    });
  });

  return getLayoutedElements(nodes, edges, "TB");
}

export function DAGView({ outline }: DAGViewProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (!outline) return { nodes: [], edges: [] };
    return buildNodesAndEdges(outline);
  }, [outline]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Update nodes when outline changes
  React.useEffect(() => {
    if (outline) {
      const { nodes: newNodes, edges: newEdges } = buildNodesAndEdges(outline);
      setNodes(newNodes);
      setEdges(newEdges);
    }
  }, [outline, setNodes, setEdges]);

  if (!outline) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        Validate a scenario to see the DAG visualization
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        No nodes to display
      </div>
    );
  }

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        attributionPosition="bottom-left"
      >
        <Background color="#e5e7eb" gap={16} />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            if (node.id.startsWith("signal-")) return NODE_COLORS.signal.border;
            if (node.id.startsWith("trend-")) return NODE_COLORS.trend.border;
            if (node.id.startsWith("logic-")) return NODE_COLORS.logic.border;
            return "#999";
          }}
          maskColor="rgba(0,0,0,0.1)"
        />
      </ReactFlow>

      {/* Legend */}
      <div className="absolute bottom-4 right-4 bg-white p-3 rounded-lg shadow-lg border text-sm">
        <div className="font-semibold mb-2">Legend</div>
        <div className="flex items-center gap-2 mb-1">
          <div
            className="w-4 h-4 rounded"
            style={{ background: NODE_COLORS.signal.bg, border: `2px solid ${NODE_COLORS.signal.border}` }}
          />
          <span>Signal (data source)</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div
            className="w-4 h-4 rounded"
            style={{ background: NODE_COLORS.trend.bg, border: `2px solid ${NODE_COLORS.trend.border}` }}
          />
          <span>Trend (computation)</span>
        </div>
        <div className="flex items-center gap-2">
          <div
            className="w-4 h-4 rounded"
            style={{ background: NODE_COLORS.logic.bg, border: `2px solid ${NODE_COLORS.logic.border}` }}
          />
          <span>Logic (decision)</span>
        </div>
      </div>
    </div>
  );
}
