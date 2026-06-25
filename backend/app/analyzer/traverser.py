"""Walk a local repository and yield analysable source files."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .languages import EXT_TO_LANG

# Directories we never descend into.
IGNORED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    "env", ".env", "dist", "build", "out", "target", ".next", ".nuxt",
    "coverage", ".pytest_cache", ".mypy_cache", ".idea", ".vscode",
    "vendor", "bin", "obj", ".cache", ".turbo", ".gradle", "site-packages",
}


@dataclass
class FileRecord:
    """A discovered source file."""

    abs_path: Path
    rel_path: str          # posix-style, relative to repo root
    language: str
    size_bytes: int


def _should_skip_dir(name: str) -> bool:
    return name in IGNORED_DIRS or (name.startswith(".") and name not in {".github"})


def traverse(root: Path) -> list[FileRecord]:
    """Return source files under ``root`` (recursively).

    Hidden and dependency directories are skipped, as are files whose
    extension is not a recognised source language.
    """
    root = root.resolve()
    records: list[FileRecord] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored directories in place so os.walk does not descend.
        dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]

        for fname in filenames:
            ext = Path(fname).suffix.lower()
            lang = EXT_TO_LANG.get(ext)
            if not lang:
                continue
            abs_path = Path(dirpath) / fname
            try:
                size = abs_path.stat().st_size
            except OSError:
                continue
            rel = abs_path.relative_to(root).as_posix()
            records.append(
                FileRecord(
                    abs_path=abs_path,
                    rel_path=rel,
                    language=lang,
                    size_bytes=size,
                )
            )

    records.sort(key=lambda r: r.rel_path)
    return records
