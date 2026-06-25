"""Resolve raw imports to concrete files inside the repository.

The resolver only ever produces edges *between files that exist in the repo*.
Third-party / standard-library references are detected but intentionally
dropped, because the goal is to show how a project's own files interact.
"""
from __future__ import annotations

import posixpath
import re
from pathlib import Path

from .dependency_parser import RawImport
from .traverser import FileRecord

_JS_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
_PY_EXTS = (".py", ".pyi")


def _norm(base_dir: str, rel: str) -> str | None:
    """Join ``rel`` onto ``base_dir`` and normalise, or None if it escapes root."""
    joined = posixpath.normpath(posixpath.join(base_dir, rel))
    if joined.startswith("..") or joined == "..":
        return None
    return joined.lstrip("./") or None


class Resolver:
    """Resolve imports against a fixed snapshot of repository files."""

    def __init__(self, root: Path, records: list[FileRecord]) -> None:
        self.root = root
        self.files: set[str] = {r.rel_path for r in records}
        self._by_basename: dict[str, list[str]] = {}
        for rel in self.files:
            self._by_basename.setdefault(posixpath.basename(rel), []).append(rel)
        self.go_module = self._read_go_module(root)

    # ----------------------------------------------------------------- #
    # Public entry point
    # ----------------------------------------------------------------- #
    def resolve(self, rec: FileRecord, imports: list[RawImport]) -> list[tuple[str, str]]:
        """Return a deduplicated list of ``(target_rel_path, kind)`` edges."""
        edges: list[tuple[str, str]] = []
        seen: set[str] = set()
        for imp in imports:
            target = self._resolve_one(rec, imp)
            if target and target != rec.rel_path and target not in seen:
                seen.add(target)
                kind = "include" if imp.kind.startswith("include") else imp.kind
                edges.append((target, kind))
        return edges

    # ----------------------------------------------------------------- #
    # Per-language dispatch
    # ----------------------------------------------------------------- #
    def _resolve_one(self, rec: FileRecord, imp: RawImport) -> str | None:
        lang = rec.language
        if lang == "python":
            return self._resolve_python(rec, imp)
        if lang in ("javascript", "typescript"):
            return self._resolve_js(rec, imp)
        if lang in ("c", "cpp"):
            return self._resolve_c(rec, imp)
        if lang == "java":
            return self._resolve_java(imp)
        if lang == "go":
            return self._resolve_go(imp)
        return None

    # ----------------------------------------------------------------- #
    # Python
    # ----------------------------------------------------------------- #
    def _module_candidates(self, dotted: str) -> list[str]:
        parts = [p for p in dotted.split(".") if p]
        if not parts:
            return []
        base = "/".join(parts)
        cands = [base + ext for ext in _PY_EXTS]
        cands += [f"{base}/__init__{ext}" for ext in _PY_EXTS]
        return cands

    def _resolve_python(self, rec: FileRecord, imp: RawImport) -> str | None:
        if imp.is_relative:
            stripped = imp.target.lstrip(".")
            dots = len(imp.target) - len(stripped)
            base_dir = posixpath.dirname(rec.rel_path)
            up = posixpath.normpath(posixpath.join(base_dir, *([".."] * (dots - 1)))) \
                if dots > 1 else base_dir
            up = "" if up == "." else up
            sub = stripped.replace(".", "/")
            target = posixpath.join(up, sub) if sub else up
            for ext in _PY_EXTS:
                for cand in (f"{target}{ext}", f"{target}/__init__{ext}"):
                    cand = cand.lstrip("/")
                    if cand in self.files:
                        return cand
            return None
        # Absolute import resolved against repo root.
        for cand in self._module_candidates(imp.target):
            if cand in self.files:
                return cand
        return None

    # ----------------------------------------------------------------- #
    # JavaScript / TypeScript
    # ----------------------------------------------------------------- #
    def _resolve_js(self, rec: FileRecord, imp: RawImport) -> str | None:
        if not imp.is_relative:
            return None  # bare specifier -> node_modules, ignored
        base_dir = posixpath.dirname(rec.rel_path)
        target = _norm(base_dir, imp.target)
        if target is None:
            return None
        # Exact file (import already includes extension).
        if target in self.files:
            return target
        # Try appending known extensions.
        for ext in _JS_EXTS:
            if f"{target}{ext}" in self.files:
                return f"{target}{ext}"
        # Try directory index files.
        for ext in _JS_EXTS:
            if f"{target}/index{ext}" in self.files:
                return f"{target}/index{ext}"
        return None

    # ----------------------------------------------------------------- #
    # C / C++
    # ----------------------------------------------------------------- #
    def _resolve_c(self, rec: FileRecord, imp: RawImport) -> str | None:
        if imp.kind == "include_system":
            return None
        base_dir = posixpath.dirname(rec.rel_path)
        target = _norm(base_dir, imp.target)
        if target and target in self.files:
            return target
        # Fall back to a basename search across the repo.
        base = posixpath.basename(imp.target)
        matches = self._by_basename.get(base, [])
        if not matches:
            return None
        if len(matches) == 1:
            return matches[0]
        top = rec.rel_path.split("/", 1)[0]
        same_top = [m for m in matches if m.startswith(top + "/")]
        return (same_top or matches)[0]

    # ----------------------------------------------------------------- #
    # Java
    # ----------------------------------------------------------------- #
    def _resolve_java(self, imp: RawImport) -> str | None:
        if imp.target.endswith(".*"):
            return None
        parts = imp.target.split(".")
        # Drop trailing segments (e.g. static member) until a .java file matches.
        for end in range(len(parts), 0, -1):
            suffix = "/".join(parts[:end]) + ".java"
            for rel in self.files:
                if rel == suffix or rel.endswith("/" + suffix):
                    return rel
        return None

    # ----------------------------------------------------------------- #
    # Go
    # ----------------------------------------------------------------- #
    def _resolve_go(self, imp: RawImport) -> str | None:
        if not self.go_module or not imp.target.startswith(self.go_module):
            return None
        sub = imp.target[len(self.go_module):].strip("/")
        # Link to the first .go file living directly in the imported package dir.
        prefix = (sub + "/") if sub else ""
        for rel in sorted(self.files):
            if not rel.endswith(".go"):
                continue
            if posixpath.dirname(rel) == sub.rstrip("/"):
                return rel
            if sub == "" and "/" not in rel:
                return rel
            if prefix and rel.startswith(prefix) and "/" not in rel[len(prefix):]:
                return rel
        return None

    @staticmethod
    def _read_go_module(root: Path) -> str | None:
        gomod = root / "go.mod"
        if not gomod.exists():
            return None
        try:
            text = gomod.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None
        m = re.search(r"^\s*module\s+(\S+)", text, re.MULTILINE)
        return m.group(1) if m else None
