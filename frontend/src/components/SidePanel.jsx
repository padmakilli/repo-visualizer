import { useCallback, useEffect, useState } from "react";
import {
  Sparkles,
  Loader2,
  ArrowDownLeft,
  ArrowUpRight,
  AlertTriangle,
  RotateCw,
  FileCode2,
} from "lucide-react";
import { explainFile, getFile } from "../api/client.js";
import {
  langColor,
  complexityColor,
  complexityLabel,
} from "../utils/colors.js";

function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function Metric({ label, value, accent }) {
  return (
    <div className="metric">
      <span className="metric__value" style={accent ? { color: accent } : undefined}>
        {value}
      </span>
      <span className="metric__label">{label}</span>
    </div>
  );
}

export default function SidePanel({ node, root }) {
  const [summary, setSummary] = useState(null);
  const [explaining, setExplaining] = useState(false);
  const [explainError, setExplainError] = useState(null);

  const [source, setSource] = useState(null);
  const [loadingSource, setLoadingSource] = useState(false);

  // Whenever the selected file changes, drop any previous AI/source state so we
  // never show one file's summary next to another file's name.
  useEffect(() => {
    setSummary(null);
    setExplaining(false);
    setExplainError(null);
    setSource(null);

    if (!node) return;
    let alive = true;
    setLoadingSource(true);
    getFile(root, node.path)
      .then((data) => alive && setSource(data))
      .catch(() => alive && setSource(null))
      .finally(() => alive && setLoadingSource(false));
    return () => {
      alive = false;
    };
  }, [node, root]);

  const runExplain = useCallback(
    async (force = false) => {
      if (!node) return;
      setExplaining(true);
      setExplainError(null);
      try {
        const res = await explainFile(root, node.path, force);
        setSummary(res);
      } catch (err) {
        setExplainError(err.message || "Failed to generate summary.");
      } finally {
        setExplaining(false);
      }
    },
    [node, root]
  );

  if (!node) {
    return (
      <aside className="side-panel side-panel--empty">
        <FileCode2 size={26} className="side-panel__empty-icon" />
        <p className="side-panel__empty-title">No file selected</p>
        <p className="side-panel__empty-text">
          Click any node on the canvas to inspect its metrics, read its source,
          and generate a plain-English summary.
        </p>
      </aside>
    );
  }

  const accent = langColor(node.language);
  const heat = complexityColor(node.complexity);
  const isNull = summary && summary.provider === "none";

  return (
    <aside className="side-panel">
      <div className="side-panel__head">
        <span className="side-panel__pin" style={{ background: accent }} />
        <div className="side-panel__id">
          <div className="side-panel__name" title={node.path}>
            {node.label}
          </div>
          <div className="side-panel__path">{node.path}</div>
        </div>
      </div>

      <div className="side-panel__lang">
        <span className="lang-pill" style={{ "--pin": accent }}>
          {node.language}
        </span>
        <span className="side-panel__size">{formatBytes(node.size_bytes)}</span>
      </div>

      <div className="metric-grid">
        <Metric label="lines" value={node.loc} />
        <Metric label="source lines" value={node.sloc} />
        <Metric label="complexity" value={node.complexity} accent={heat} />
        <Metric
          label="imported by"
          value={
            <span className="metric__deg">
              <ArrowDownLeft size={13} /> {node.in_degree}
            </span>
          }
        />
        <Metric
          label="imports"
          value={
            <span className="metric__deg">
              <ArrowUpRight size={13} /> {node.out_degree}
            </span>
          }
        />
        <Metric
          label="heat"
          value={complexityLabel(node.complexity)}
          accent={heat}
        />
      </div>

      <div className="ai-block">
        <div className="ai-block__head">
          <Sparkles size={15} className="ai-block__spark" />
          <span>AI summary</span>
          {summary && summary.cached && !isNull && (
            <span className="ai-badge">cached</span>
          )}
        </div>

        {!summary && !explaining && !explainError && (
          <button className="btn btn--ai" onClick={() => runExplain(false)}>
            <Sparkles size={15} />
            Explain this file
          </button>
        )}

        {explaining && (
          <div className="ai-block__loading">
            <Loader2 size={15} className="spin" />
            Reading the code…
          </div>
        )}

        {explainError && (
          <div className="ai-block__error">
            <AlertTriangle size={14} />
            <span>{explainError}</span>
            <button className="btn btn--ghost btn--sm" onClick={() => runExplain(false)}>
              <RotateCw size={13} /> Retry
            </button>
          </div>
        )}

        {summary && (
          <div className="ai-block__result">
            <p className={`ai-summary${isNull ? " ai-summary--muted" : ""}`}>
              {summary.summary}
            </p>
            <div className="ai-block__foot">
              <span className="ai-block__model">
                {isNull
                  ? "no AI provider configured"
                  : `${summary.provider} · ${summary.model}`}
              </span>
              {!isNull && (
                <button
                  className="btn btn--ghost btn--sm"
                  onClick={() => runExplain(true)}
                  disabled={explaining}
                  title="Bypass cache and re-summarize"
                >
                  <RotateCw size={13} /> Re-run
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="source-block">
        <div className="source-block__head">
          <span>Source</span>
          {source && source.truncated && (
            <span className="source-block__note">truncated</span>
          )}
        </div>
        {loadingSource ? (
          <div className="source-block__loading">
            <Loader2 size={14} className="spin" /> loading…
          </div>
        ) : source && source.content ? (
          <pre className="source-block__code">
            <code>{source.content}</code>
          </pre>
        ) : (
          <div className="source-block__empty">No readable source.</div>
        )}
      </div>
    </aside>
  );
}
