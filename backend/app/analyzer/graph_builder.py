"""Build the dependency graph (nodes + edges) for a repository."""
from __future__ import annotations

import posixpath
from collections import Counter, defaultdict
from pathlib import Path

from ..models import GraphEdge, GraphNode, GraphResponse, GraphStats
from .dependency_parser import parse_imports
from .metrics import Metrics, compute_metrics
from .resolver import Resolver
from .traverser import FileRecord, traverse


def read_text(path: Path, max_bytes: int) -> tuple[str, bool]:
    """Read a file as UTF-8 text. Returns ``(text, truncated)``.

    Files larger than ``max_bytes`` are read up to the limit and flagged as
    truncated. Undecodable bytes are replaced rather than raising.
    """
    try:
        size = path.stat().st_size
    except OSError:
        return "", False
    truncated = size > max_bytes
    try:
        with path.open("rb") as fh:
            data = fh.read(max_bytes if truncated else size)
    except OSError:
        return "", False
    return data.decode("utf-8", errors="replace"), truncated


def build_graph(root: Path, max_bytes: int) -> GraphResponse:
    """Analyse ``root`` and return the full :class:`GraphResponse`."""
    root = root.resolve()
    records: list[FileRecord] = traverse(root)
    resolver = Resolver(root, records)

    nodes: dict[str, GraphNode] = {}
    metrics_by_path: dict[str, Metrics] = {}
    imports_by_path: dict[str, list] = {}
    skipped = 0

    for rec in records:
        text, truncated = read_text(rec.abs_path, max_bytes)
        if truncated or not text:
            metrics = Metrics(loc=0, sloc=0, complexity=0)
            if truncated:
                skipped += 1
        else:
            metrics = compute_metrics(text, rec.language)
        metrics_by_path[rec.rel_path] = metrics
        imports_by_path[rec.rel_path] = parse_imports(rec.language, text) if text else []

        nodes[rec.rel_path] = GraphNode(
            id=rec.rel_path,
            label=posixpath.basename(rec.rel_path),
            path=rec.rel_path,
            dir=posixpath.dirname(rec.rel_path),
            language=rec.language,
            loc=metrics.loc,
            sloc=metrics.sloc,
            complexity=metrics.complexity,
            size_bytes=rec.size_bytes,
        )

    # Resolve edges.
    edges: list[GraphEdge] = []
    edge_keys: set[tuple[str, str]] = set()
    out_degree: Counter[str] = Counter()
    in_degree: Counter[str] = Counter()

    for rec in records:
        for target, kind in resolver.resolve(rec, imports_by_path[rec.rel_path]):
            key = (rec.rel_path, target)
            if key in edge_keys or target not in nodes:
                continue
            edge_keys.add(key)
            edges.append(
                GraphEdge(
                    id=f"{rec.rel_path}->{target}",
                    source=rec.rel_path,
                    target=target,
                    kind=kind,
                )
            )
            out_degree[rec.rel_path] += 1
            in_degree[target] += 1

    for path, node in nodes.items():
        node.in_degree = in_degree.get(path, 0)
        node.out_degree = out_degree.get(path, 0)

    languages: Counter[str] = Counter(n.language for n in nodes.values())
    total_loc = sum(n.loc for n in nodes.values())

    stats = GraphStats(
        root=str(root),
        file_count=len(nodes),
        edge_count=len(edges),
        total_loc=total_loc,
        languages=dict(languages),
        skipped=skipped,
    )

    return GraphResponse(
        root=str(root),
        nodes=list(nodes.values()),
        edges=edges,
        stats=stats,
    )
