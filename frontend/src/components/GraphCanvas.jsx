import { useCallback } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
} from "reactflow";
import "reactflow/dist/style.css";

import FileNode from "./FileNode.jsx";
import { langColor } from "../utils/colors.js";

// Registered once at module scope (re-creating this object each render makes
// React Flow warn and remount nodes).
const nodeTypes = { fileNode: FileNode };

export default function GraphCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onSelect,
}) {
  const handleNodeClick = useCallback(
    (_evt, node) => onSelect(node.id),
    [onSelect]
  );
  const handlePaneClick = useCallback(() => onSelect(null), [onSelect]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={handleNodeClick}
      onPaneClick={handlePaneClick}
      fitView
      minZoom={0.1}
      maxZoom={2}
      proOptions={{ hideAttribution: true }}
      defaultEdgeOptions={{ type: "default" }}
    >
      <Background variant={BackgroundVariant.Dots} gap={26} size={1} color="#222b36" />
      <MiniMap
        pannable
        zoomable
        maskColor="rgba(14,17,22,0.78)"
        nodeColor={(n) => langColor(n.data?.language)}
        nodeStrokeWidth={0}
        style={{ background: "#11161d", border: "1px solid #2a323d" }}
      />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}
