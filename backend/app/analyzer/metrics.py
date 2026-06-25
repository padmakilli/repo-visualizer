"""Compute simple, language-aware code metrics without executing code."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .languages import BLOCK_COMMENT, LINE_COMMENT

# Decision-point keywords/operators counted for the complexity approximation.
# This is McCabe-style: complexity = 1 + number of branch points.
_DECISION_WORDS = {
    "python": ("if", "elif", "for", "while", "except", "with", "assert"),
    "javascript": ("if", "for", "while", "case", "catch"),
    "typescript": ("if", "for", "while", "case", "catch"),
    "c": ("if", "for", "while", "case"),
    "cpp": ("if", "for", "while", "case", "catch"),
    "java": ("if", "for", "while", "case", "catch"),
    "go": ("if", "for", "case", "select"),
    "ruby": ("if", "elsif", "for", "while", "case", "rescue", "unless"),
    "rust": ("if", "for", "while", "match"),
}
_DEFAULT_WORDS = ("if", "for", "while", "case", "catch")
# Boolean operators add independent paths too.
_DECISION_OPS = ("&&", "||", " and ", " or ", "?")


@dataclass
class Metrics:
    loc: int          # total physical lines
    sloc: int         # source lines (no blanks, no comment-only lines)
    complexity: int   # approximate cyclomatic complexity


def _strip_block_comments(text: str, language: str) -> str:
    markers = BLOCK_COMMENT.get(language)
    if not markers:
        return text
    open_m, close_m = markers
    pattern = re.escape(open_m) + r".*?" + re.escape(close_m)
    return re.sub(pattern, " ", text, flags=re.DOTALL)


def compute_metrics(text: str, language: str) -> Metrics:
    """Return :class:`Metrics` for ``text`` in the given ``language``."""
    raw_lines = text.splitlines()
    loc = len(raw_lines)

    line_markers = LINE_COMMENT.get(language, ())
    sloc = 0
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if line_markers and any(stripped.startswith(m) for m in line_markers):
            continue
        sloc += 1

    # Complexity is computed on text with block comments and strings removed so
    # that keywords inside comments/strings do not inflate the count.
    code = _strip_block_comments(text, language)
    code = re.sub(r'"(?:\\.|[^"\\])*"', '""', code)
    code = re.sub(r"'(?:\\.|[^'\\])*'", "''", code)

    words = _DECISION_WORDS.get(language, _DEFAULT_WORDS)
    complexity = 1
    for w in words:
        complexity += len(re.findall(rf"\b{re.escape(w)}\b", code))
    for op in _DECISION_OPS:
        complexity += code.count(op)

    return Metrics(loc=loc, sloc=sloc, complexity=complexity)
