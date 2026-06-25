import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  useNodesState,
  useEdgesState,
  MarkerType,
} from "reactflow";
import { AlertTriangle, X, Boxes } from "lucide-react";

import Toolbar from "./components/Toolbar.jsx";
import GraphCanvas from "./components/GraphCanvas.jsx";
import SidePanel from "./components/SidePanel.jsx";
import Legend from "./components/Legend.jsx";
import { analyzeRepo } from "./api/client.js";
import { computeLayout } from "./utils/layout.js";
import "./App.css";

const EDGE_BASE = { stroke: "#39424f", strokeWidth: 1.1, opacity: 0.55 };
const EDGE_DIM = { stroke: "#39424f", strokeWidth: 1, opacity: 0.1 };
const EDGE_ACTIVE = { stroke: "#f0a830", strokeWidth: 1.8, opacity: 0.95 };

function marker(color) {
  return { type: MarkerType.ArrowClosed, color, width: 14, height: 14 };
}

function buildElements(graph) {
  const positions = computeLayout(graph.nodes);
  const nodes = graph.nodes.map((n) => ({
    id: n.id,
    type: "fileNode",
    position: positions[n.id] || { x: 0, y: 0 },
    data: { ...n, faded: false },
  }));
  const edges = graph.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: "default",
    style: EDGE_BASE,
    markerEnd: marker(EDGE_BASE.stroke),
  }));
  return { nodes, edges };
}

export default function App() {
  const [path, setPath] = useState("");
  const [graph, setGraph] = useState(null);
  const [root, setRoot] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Adjacency derived from the raw graph — used to decide what stays lit when a
  // node is selected. Rebuilt only when a new graph loads.
  const neighbors = useMemo(() => {
    const map = new Map();
    if (!graph) return map;
    for (const e of graph.edges) {
      if (!map.has(e.source)) map.set(e.source, new Set());
      if (!map.has(e.target)) map.set(e.target, new Set());
      map.get(e.source).add(e.target);
      map.get(e.target).add(e.source);
    }
    return map;
  }, [graph]);

  const runAnalyze = useCallback(async () => {
    const target = path.trim();
    if (!target || loading) return;
    setLoading(true);
    setError(null);
    setSelectedId(null);
    try {
      const data = await analyzeRepo(target);
      setGraph(data);
      setRoot(data.root);
      const { nodes: n, edges: e } = buildElements(data);
      setNodes(n);
      setEdges(e);
    } catch (err) {
      setError(err.message || "Analysis failed.");
      setGraph(null);
      setNodes([]);
      setEdges([]);
    } finally {
      setLoading(false);
    }
  }, [path, loading, setNodes, setEdges]);

  const relayout = useCallback(() => {
    if (!graph) return;
    const positions = computeLayout(graph.nodes);
    setNodes((nds) =>
      nds.map((n) => ({ ...n, position: positions[n.id] || n.position }))
    );
  }, [graph, setNodes]);

  // Re-derive fade + highlight whenever the selection changes. Position lives in
  // node state and is preserved here, so dragging is never lost.
  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) => {
        const selected = n.id === selectedId;
        let faded = false;
        if (selectedId && !selected) {
          const set = neighbors.get(selectedId);
          faded = !(set && set.has(n.id));
        }
        if (n.selected === selected && n.data.faded === faded) return n;
        return { ...n, selected, data: { ...n.data, faded } };
      })
    );

    setEdges((eds) =>
      eds.map((e) => {
        let style = EDGE_BASE;
        if (selectedId) {
          const active = e.source === selectedId || e.target === selectedId;
          style = active ? EDGE_ACTIVE : EDGE_DIM;
        }
        return {
          ...e,
          animated: selectedId
            ? e.source === selectedId || e.target === selectedId
            : false,
          style,
          markerEnd: marker(style.stroke),
          zIndex: style === EDGE_ACTIVE ? 10 : 0,
        };
      })
    );
  }, [selectedId, neighbors, setNodes, setEdges]);

  const selectedNode = useMemo(
    () => (graph && selectedId ? graph.nodes.find((n) => n.id === selectedId) : null),
    [graph, selectedId]
  );

  return (
    <div className="app">
      <Toolbar
        path={path}
        onPathChange={setPath}
        onAnalyze={runAnalyze}
        onRelayout={relayout}
        loading={loading}
        stats={graph ? graph.stats : null}
        hasGraph={!!graph}
      />

      {error && (
        <div className="error-banner">
          <AlertTriangle size={15} />
          <span>{error}</span>
          <button className="error-banner__close" onClick={() => setError(null)}>
            <X size={15} />
          </button>
        </div>
      )}

      <main className="workspace">
        <div className="canvas-wrap">
          {graph ? (
            <>
              <GraphCanvas
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onSelect={setSelectedId}
              />
              <Legend languages={graph.stats.languages} />
            </>
          ) : (
            <div className="empty-canvas">
              <Boxes size={40} className="empty-canvas__icon" />
              <h2 className="empty-canvas__title">Map a codebase</h2>
              <p className="empty-canvas__text">
                Paste the absolute path to a local repository above and hit{" "}
                <strong>Analyze</strong>. The engine traverses files, extracts
                imports statically (nothing is executed), and draws an
                interactive dependency graph.
              </p>
              <p className="empty-canvas__hint">
                Tip: point it at this project's own backend folder for a quick demo.
              </p>
            </div>
          )}
        </div>

        <SidePanel node={selectedNode} root={root} />
      </main>
    </div>
  );
}
