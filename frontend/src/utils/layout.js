// Compute initial node positions. Files are grouped into columns by their
// top-level directory so related modules cluster together; long folders wrap
// into sub-columns. Users can freely drag nodes afterwards.

const COL_W = 240;
const ROW_H = 104;
const MAX_ROWS = 14;
const GROUP_GAP = 64;

function topGroup(path) {
  const idx = path.indexOf("/");
  return idx === -1 ? "·root" : path.slice(0, idx);
}

export function computeLayout(nodes) {
  const groups = new Map();
  for (const n of nodes) {
    const g = topGroup(n.path);
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g).push(n);
  }

  const orderedGroups = [...groups.keys()].sort((a, b) => a.localeCompare(b));
  const positions = {};
  let xCursor = 0;

  for (const g of orderedGroups) {
    const files = groups.get(g).sort((a, b) => a.path.localeCompare(b.path));
    const subCols = Math.ceil(files.length / MAX_ROWS);
    files.forEach((file, i) => {
      const col = Math.floor(i / MAX_ROWS);
      const row = i % MAX_ROWS;
      positions[file.id] = {
        x: xCursor + col * COL_W,
        y: row * ROW_H,
      };
    });
    xCursor += subCols * COL_W + GROUP_GAP;
  }

  return positions;
}
