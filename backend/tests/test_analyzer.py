"""Tests for the static-analysis engine."""
from __future__ import annotations

from pathlib import Path

from app.analyzer.dependency_parser import parse_imports
from app.analyzer.graph_builder import build_graph
from app.analyzer.metrics import compute_metrics


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def test_parse_python_imports():
    src = "import os\nfrom app.analyzer import metrics\nfrom . import sibling\n"
    targets = {imp.target for imp in parse_imports("python", src)}
    assert "os" in targets
    assert "app.analyzer.metrics" in targets
    assert any(t.startswith(".") for t in targets)


def test_parse_js_imports():
    src = (
        "import React from 'react';\n"
        "import { foo } from './utils/foo';\n"
        "const x = require('../lib/x');\n"
    )
    imps = parse_imports("javascript", src)
    targets = {i.target for i in imps}
    assert "react" in targets
    assert "./utils/foo" in targets
    assert "../lib/x" in targets
    # react is a bare specifier -> not relative
    assert any(i.target == "react" and not i.is_relative for i in imps)


def test_parse_c_includes():
    src = '#include <stdio.h>\n#include "engine.h"\n'
    imps = parse_imports("c", src)
    kinds = {i.target: i.kind for i in imps}
    assert kinds["engine.h"] == "include"
    assert kinds["stdio.h"] == "include_system"


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def test_metrics_counts_lines_and_complexity():
    src = (
        "def f(x):\n"
        "    # a comment\n"
        "\n"
        "    if x > 0 and x < 10:\n"
        "        for i in range(x):\n"
        "            print(i)\n"
    )
    m = compute_metrics(src, "python")
    assert m.loc == 6
    assert m.sloc == 4          # comment + blank excluded
    assert m.complexity >= 3    # base 1 + if + for (+ 'and')


# --------------------------------------------------------------------------- #
# Graph build (integration on a synthetic repo)
# --------------------------------------------------------------------------- #
def _write(base: Path, rel: str, text: str) -> None:
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_build_graph_resolves_python_edges(tmp_path: Path):
    _write(tmp_path, "pkg/__init__.py", "")
    _write(tmp_path, "pkg/util.py", "VALUE = 1\n")
    _write(tmp_path, "pkg/core.py", "from pkg.util import VALUE\nimport os\n")
    _write(tmp_path, "main.py", "from pkg import core\n")
    # Noise that must be ignored.
    _write(tmp_path, "node_modules/dep/index.js", "module.exports = {};\n")

    graph = build_graph(tmp_path, max_bytes=1_000_000)
    ids = {n.id for n in graph.nodes}

    assert "pkg/util.py" in ids
    assert "main.py" in ids
    assert "node_modules/dep/index.js" not in ids  # pruned

    edges = {(e.source, e.target) for e in graph.edges}
    assert ("pkg/core.py", "pkg/util.py") in edges
    assert ("main.py", "pkg/core.py") in edges
    # External 'os' import produced no edge.
    assert all(e.target != "os" for e in graph.edges)


def test_build_graph_resolves_js_and_c(tmp_path: Path):
    _write(tmp_path, "src/index.js", "import { add } from './math/add';\n")
    _write(tmp_path, "src/math/add.js", "export const add = (a, b) => a + b;\n")
    _write(tmp_path, "native/main.c", '#include "engine.h"\nint main(){return 0;}\n')
    _write(tmp_path, "native/engine.h", "#ifndef ENGINE_H\n#define ENGINE_H\n#endif\n")

    graph = build_graph(tmp_path, max_bytes=1_000_000)
    edges = {(e.source, e.target) for e in graph.edges}
    assert ("src/index.js", "src/math/add.js") in edges
    assert ("native/main.c", "native/engine.h") in edges


def test_degrees_are_computed(tmp_path: Path):
    # Both `import b` and `from b import VALUE` resolve to the repo's b.py.
    _write(tmp_path, "a.py", "import b\n")
    _write(tmp_path, "b.py", "VALUE = 1\n")
    _write(tmp_path, "c.py", "from b import VALUE\n")

    graph = build_graph(tmp_path, max_bytes=1_000_000)
    by_id = {n.id: n for n in graph.nodes}
    assert by_id["b.py"].in_degree == 2   # a.py and c.py both import b
    assert by_id["a.py"].out_degree == 1
    assert by_id["c.py"].out_degree == 1
