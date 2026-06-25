// Functional colour mapping. Colour here encodes language and complexity, so a
// multi-hue palette is meaningful information rather than decoration.

export const LANG_COLORS = {
  python: "#6E9FE6",
  javascript: "#E8C547",
  typescript: "#3B82F6",
  c: "#8A93A0",
  cpp: "#A07BD6",
  java: "#E0734F",
  go: "#34C7C0",
  ruby: "#E0556B",
  rust: "#C98A52",
  php: "#8E84D8",
  csharp: "#67C28E",
  kotlin: "#C879E0",
  swift: "#F0824B",
  scala: "#E05650",
  unknown: "#6B7280",
};

export function langColor(language) {
  return LANG_COLORS[language] || LANG_COLORS.unknown;
}

// Stepped heat scale for cyclomatic complexity.
export function complexityColor(complexity) {
  if (complexity <= 5) return "#3FB68B"; // calm green
  if (complexity <= 15) return "#E0A23B"; // amber
  if (complexity <= 30) return "#E07B3B"; // orange
  return "#E0533B"; // hot red
}

// Normalised 0..1 fill ratio for the complexity bar (capped so outliers stay readable).
export function complexityRatio(complexity, cap = 40) {
  return Math.max(0.06, Math.min(1, complexity / cap));
}

export function complexityLabel(complexity) {
  if (complexity <= 5) return "low";
  if (complexity <= 15) return "moderate";
  if (complexity <= 30) return "high";
  return "very high";
}
