"""Path validation: keep file access inside analysed roots / the sandbox."""
from __future__ import annotations

from pathlib import Path

from .config import Settings


class PathError(ValueError):
    """Raised when a requested path is invalid or out of bounds."""


def _is_within(base: Path, target: Path) -> bool:
    try:
        target.relative_to(base)
        return True
    except ValueError:
        return False


def validate_root(path_str: str, settings: Settings) -> Path:
    """Resolve a repo root and confirm it exists and is allowed."""
    if not path_str or not path_str.strip():
        raise PathError("A repository path is required.")
    root = Path(path_str).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise PathError(f"Directory not found: {root}")
    sandbox = settings.repo_root_path
    if sandbox and not _is_within(sandbox, root):
        raise PathError(f"Path is outside the allowed REPO_ROOT ({sandbox}).")
    return root


def resolve_file(
    root_str: str,
    rel_path: str,
    settings: Settings,
    analyzed_roots: set[str],
) -> tuple[Path, Path]:
    """Resolve ``rel_path`` under ``root_str`` and confirm it is safe to read.

    Returns ``(root, file_path)``. The root must have been analysed already (or
    fall inside the configured sandbox), and the file must resolve to a regular
    file inside that root.
    """
    root = Path(root_str).expanduser().resolve()
    sandbox = settings.repo_root_path
    allowed = str(root) in analyzed_roots or (sandbox and _is_within(sandbox, root))
    if not allowed:
        raise PathError("Unknown root. Analyse the repository before reading files.")

    target = (root / rel_path).resolve()
    if not _is_within(root, target):
        raise PathError("Resolved path escapes the repository root.")
    if not target.exists() or not target.is_file():
        raise PathError(f"File not found: {rel_path}")
    return root, target
