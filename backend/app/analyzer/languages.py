"""Map file extensions to languages and expose per-language comment markers."""
from __future__ import annotations

from pathlib import Path

# Extension -> language name
EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".java": "java",
    ".go": "go",
    ".rb": "ruby",
    ".rs": "rust",
    ".php": "php",
    ".cs": "csharp",
    ".kt": "kotlin",
    ".swift": "swift",
    ".scala": "scala",
}

# Languages we can resolve dependencies for today.
SUPPORTED_FOR_DEPS = {"python", "javascript", "typescript", "c", "cpp", "java", "go"}

# Line + block comment markers, for the SLoC heuristic.
LINE_COMMENT: dict[str, tuple[str, ...]] = {
    "python": ("#",),
    "ruby": ("#",),
    "javascript": ("//",),
    "typescript": ("//",),
    "c": ("//",),
    "cpp": ("//",),
    "java": ("//",),
    "go": ("//",),
    "rust": ("//",),
    "php": ("//", "#"),
    "csharp": ("//",),
    "kotlin": ("//",),
    "swift": ("//",),
    "scala": ("//",),
}

BLOCK_COMMENT: dict[str, tuple[str, str]] = {
    "javascript": ("/*", "*/"),
    "typescript": ("/*", "*/"),
    "c": ("/*", "*/"),
    "cpp": ("/*", "*/"),
    "java": ("/*", "*/"),
    "go": ("/*", "*/"),
    "rust": ("/*", "*/"),
    "php": ("/*", "*/"),
    "csharp": ("/*", "*/"),
    "kotlin": ("/*", "*/"),
    "swift": ("/*", "*/"),
    "scala": ("/*", "*/"),
}


def detect_language(path: str | Path) -> str:
    """Return the language for a file path based on its extension."""
    return EXT_TO_LANG.get(Path(path).suffix.lower(), "unknown")
