import { memo } from "react";
import { Handle, Position } from "reactflow";
import {
  langColor,
  complexityColor,
  complexityRatio,
} from "../utils/colors.js";

// A file rendered as a compact "chip": a language pin on the left, the file
// name and key metrics in the body, and a complexity heat bar along the bottom.
function FileNode({ data, selected }) {
  const pin = langColor(data.language);
  const heat = complexityColor(data.complexity);
  const ratio = complexityRatio(data.complexity);

  const classes = ["file-node"];
  if (selected) classes.push("file-node--selected");
  if (data.faded) classes.push("file-node--faded");

  return (
    <div className={classes.join(" ")} style={{ "--pin": pin }}>
      <Handle type="target" position={Position.Left} className="file-node__handle" />
      <span className="file-node__pin" />
      <div className="file-node__body">
        <div className="file-node__name" title={data.path}>
          {data.label}
        </div>
        <div className="file-node__meta">
          <span className="file-node__lang">{data.language}</span>
          <span className="file-node__loc">{data.loc} LoC</span>
        </div>
      </div>
      <div className="file-node__heat-track">
        <div
          className="file-node__heat-fill"
          style={{ width: `${ratio * 100}%`, background: heat }}
        />
      </div>
      <Handle type="source" position={Position.Right} className="file-node__handle" />
    </div>
  );
}

export default memo(FileNode);
