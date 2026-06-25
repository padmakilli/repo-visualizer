import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { langColor } from "../utils/colors.js";

const HEAT_STOPS = [
  { label: "≤5", color: "#3FB68B", name: "low" },
  { label: "≤15", color: "#E0A23B", name: "moderate" },
  { label: "≤30", color: "#E07B3B", name: "high" },
  { label: "30+", color: "#E0533B", name: "very high" },
];

// A small floating key. Only languages actually present in the current graph
// are listed, so the legend stays relevant to what's on screen.
export default function Legend({ languages }) {
  const [open, setOpen] = useState(true);
  const langs = Object.entries(languages || {}).sort((a, b) => b[1] - a[1]);

  if (langs.length === 0) return null;

  return (
    <div className={`legend${open ? "" : " legend--closed"}`}>
      <button className="legend__toggle" onClick={() => setOpen((v) => !v)}>
        <span>Legend</span>
        <ChevronDown size={14} className="legend__chevron" />
      </button>

      {open && (
        <div className="legend__body">
          <div className="legend__section-title">Language</div>
          <div className="legend__langs">
            {langs.map(([lang, count]) => (
              <div className="legend__row" key={lang}>
                <span
                  className="legend__swatch"
                  style={{ background: langColor(lang) }}
                />
                <span className="legend__name">{lang}</span>
                <span className="legend__count">{count}</span>
              </div>
            ))}
          </div>

          <div className="legend__section-title">Complexity</div>
          <div className="legend__heat">
            {HEAT_STOPS.map((s) => (
              <div className="legend__heat-cell" key={s.label} title={s.name}>
                <span className="legend__heat-bar" style={{ background: s.color }} />
                <span className="legend__heat-label">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
