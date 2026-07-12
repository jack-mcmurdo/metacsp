import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "dagre";
import { useVizStore } from "@/store";

const NODE_WIDTH = 160;
const NODE_HEIGHT = 40;
const PALETTE = [
  "oklch(0.7 0.15 250)",
  "oklch(0.7 0.15 150)",
  "oklch(0.75 0.15 80)",
  "oklch(0.7 0.18 25)",
  "oklch(0.7 0.15 320)",
  "oklch(0.7 0.12 200)",
];

function classColor(cls: string, order: string[]): string {
  const index = order.indexOf(cls);
  return PALETTE[index % PALETTE.length];
}

function layout(nodes: Node[], edges: Edge[]): Node[] {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 30, ranksep: 60 });
  for (const node of nodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const edge of edges) {
    g.setEdge(edge.source, edge.target);
  }
  dagre.layout(g);
  return nodes.map((node) => {
    const pos = g.node(node.id);
    return {
      ...node,
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
    };
  });
}

function NetworkGraph() {
  const variables = useVizStore((s) => s.variables);
  const constraints = useVizStore((s) => s.constraints);
  const setSelected = useVizStore((s) => s.setSelected);
  const selected = useVizStore((s) => s.selected);

  const classOrder = useMemo(
    () => Array.from(new Set(variables.map((v) => v.class))),
    [variables],
  );

  const binaryConstraints = useMemo(
    () => constraints.filter((c) => c.from !== null && c.to !== null),
    [constraints],
  );
  const nonBinaryConstraints = useMemo(
    () => constraints.filter((c) => c.from === null || c.to === null),
    [constraints],
  );

  const { nodes, edges } = useMemo(() => {
    const nodes: Node[] = variables.map((v) => ({
      id: String(v.id),
      data: { label: `#${v.id} ${v.class}` },
      position: { x: 0, y: 0 },
      style: {
        background: classColor(v.class, classOrder),
        color: "white",
        border: selected?.kind === "variable" && selected.id === String(v.id) ? "2px solid white" : "none",
        borderRadius: 6,
        fontSize: 11,
        width: NODE_WIDTH,
        padding: 6,
      },
    }));
    const edges: Edge[] = binaryConstraints.map((c, i) => ({
      id: `e${i}`,
      source: String(c.from),
      target: String(c.to),
      label: c.class,
      style: { opacity: 0.6 },
      labelStyle: { fontSize: 10 },
    }));
    return { nodes: layout(nodes, edges), edges };
  }, [variables, binaryConstraints, classOrder, selected]);

  if (variables.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        Waiting for solver…
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodeClick={(_, node) => {
          const v = variables.find((v) => String(v.id) === node.id);
          if (v) setSelected({ kind: "variable", id: node.id, data: v });
        }}
        onPaneClick={() => setSelected(null)}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap pannable zoomable />
      </ReactFlow>
      {nonBinaryConstraints.length > 0 && (
        <div className="absolute bottom-3 left-3 max-h-40 max-w-xs overflow-y-auto rounded-md border bg-popover/95 p-2 text-xs shadow-md">
          <div className="mb-1 font-medium">Non-binary constraints ({nonBinaryConstraints.length})</div>
          {nonBinaryConstraints.map((c, i) => (
            <div key={i} className="truncate text-muted-foreground">
              {c.class}: {c.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function NetworkView() {
  return (
    <ReactFlowProvider>
      <NetworkGraph />
    </ReactFlowProvider>
  );
}
