import { Boxes, Play, RefreshCw, Loader2 } from "lucide-react";
import { langColor } from "../utils/colors.js";

function StatChip({ label, value }) {
  return (
    <div className="stat-chip">
      <span className="stat-chip__value">{value}</span>
      <span className="stat-chip__label">{label}</span>
    </div>
  );
}

export default function Toolbar({
  path,
  onPathChange,
  onAnalyze,
  onRelayout,
  loading,
  stats,
  hasGraph,
}) {
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !loading) onAnalyze();
  };

  return (
    <header className="toolbar">
      <div className="toolbar__brand">
        <Boxes size={20} className="toolbar__logo" />
        <div className="toolbar__title">
          <span className="toolbar__name">repo-visualizer</span>
          <span className="toolbar__sub">codebase schematic</span>
        </div>
      </div>

      <div className="toolbar__search">
        <span className="toolbar__prompt">$</span>
        <input
          className="toolbar__input"
          value={path}
          spellCheck={false}
          placeholder="/absolute/path/to/a/local/repository"
          onChange={(e) => onPathChange(e.target.value)}
          onKeyDown={handleKeyDown}
          aria-label="Repository path"
        />
        <button className="btn btn--primary" onClick={onAnalyze} disabled={loading}>
          {loading ? (
            <Loader2 size={15} className="spin" />
          ) : (
            <Play size={15} />
          )}
          {loading ? "Analyzing" : "Analyze"}
        </button>
        {hasGraph && (
          <button
            className="btn btn--ghost"
            onClick={onRelayout}
            disabled={loading}
            title="Reset node positions"
          >
            <RefreshCw size={15} />
            Re-layout
          </button>
        )}
      </div>

      <div className="toolbar__stats">
        {stats ? (
          <>
            <StatChip label="files" value={stats.file_count} />
            <StatChip label="edges" value={stats.edge_count} />
            <StatChip label="lines" value={stats.total_loc.toLocaleString()} />
            <div className="toolbar__langs">
              {Object.entries(stats.languages)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 6)
                .map(([lang, count]) => (
                  <span className="lang-tag" key={lang}>
                    <span
                      className="lang-tag__dot"
                      style={{ background: langColor(lang) }}
                    />
                    {lang} {count}
                  </span>
                ))}
            </div>
          </>
        ) : (
          <span className="toolbar__hint">point it at a repo to begin</span>
        )}
      </div>
    </header>
  );
}
