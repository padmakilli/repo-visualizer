"""Extract import/include targets from source text using regular expressions.

This is purely *static*: nothing in here imports, executes, or evaluates the
analysed code. Each parser returns a list of ``RawImport`` records describing
what a file references; resolving those references to concrete files in the
repository is the job of :mod:`resolver`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class RawImport:
    """A reference discovered in a source file."""

    target: str          # the literal module/path/header text
    kind: str            # import | from | require | include | include_system
    is_relative: bool    # starts with '.' or './' etc. (a local reference)


# --------------------------------------------------------------------------- #
# Python
# --------------------------------------------------------------------------- #
_PY_IMPORT = re.compile(r"^\s*import\s+([\w\.]+(?:\s*,\s*[\w\.]+)*)", re.MULTILINE)
_PY_FROM = re.compile(r"^\s*from\s+(\.*[\w\.]*)\s+import\s+(.+)", re.MULTILINE)


def parse_python(text: str) -> list[RawImport]:
    out: list[RawImport] = []
    for m in _PY_IMPORT.finditer(text):
        for part in m.group(1).split(","):
            name = part.strip()
            if name:
                out.append(RawImport(name, "import", is_relative=False))
    for m in _PY_FROM.finditer(text):
        module = m.group(1).strip()
        names = m.group(2)
        is_rel = module.startswith(".")
        if module in {"", "."} or is_rel:
            # Relative import: keep the dotted module plus each imported name so
            # the resolver can try `pkg.name` -> file as well as the package.
            imported = [n.strip().split(" as ")[0] for n in names.split(",")]
            for n in imported:
                if n and n != "*":
                    joined = f"{module}{n}" if module.endswith(".") else f"{module}.{n}"
                    out.append(RawImport(joined, "from", is_relative=True))
            out.append(RawImport(module, "from", is_relative=True))
        else:
            imported = [n.strip().split(" as ")[0] for n in names.split(",")]
            for n in imported:
                if n and n != "*":
                    out.append(RawImport(f"{module}.{n}", "from", is_relative=False))
            out.append(RawImport(module, "from", is_relative=False))
    return out


# --------------------------------------------------------------------------- #
# JavaScript / TypeScript
# --------------------------------------------------------------------------- #
_JS_IMPORT_FROM = re.compile(r"""import\s+[^'"]*?from\s*['"]([^'"]+)['"]""")
_JS_IMPORT_BARE = re.compile(r"""import\s*['"]([^'"]+)['"]""")
_JS_EXPORT_FROM = re.compile(r"""export\s+[^'"]*?from\s*['"]([^'"]+)['"]""")
_JS_REQUIRE = re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)""")
_JS_DYNAMIC = re.compile(r"""import\(\s*['"]([^'"]+)['"]\s*\)""")


def parse_javascript(text: str) -> list[RawImport]:
    out: list[RawImport] = []
    seen: set[tuple[str, str]] = set()

    def add(target: str, kind: str) -> None:
        key = (target, kind)
        if key in seen:
            return
        seen.add(key)
        is_rel = target.startswith(".") or target.startswith("/")
        out.append(RawImport(target, kind, is_relative=is_rel))

    for rx, kind in (
        (_JS_IMPORT_FROM, "import"),
        (_JS_IMPORT_BARE, "import"),
        (_JS_EXPORT_FROM, "import"),
        (_JS_REQUIRE, "require"),
        (_JS_DYNAMIC, "require"),
    ):
        for m in rx.finditer(text):
            add(m.group(1), kind)
    return out


# --------------------------------------------------------------------------- #
# C / C++
# --------------------------------------------------------------------------- #
_C_INCLUDE_LOCAL = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.MULTILINE)
_C_INCLUDE_SYS = re.compile(r"^\s*#\s*include\s+<([^>]+)>", re.MULTILINE)


def parse_c(text: str) -> list[RawImport]:
    out: list[RawImport] = []
    for m in _C_INCLUDE_LOCAL.finditer(text):
        out.append(RawImport(m.group(1), "include", is_relative=True))
    for m in _C_INCLUDE_SYS.finditer(text):
        out.append(RawImport(m.group(1), "include_system", is_relative=False))
    return out


# --------------------------------------------------------------------------- #
# Java
# --------------------------------------------------------------------------- #
_JAVA_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w\.]+)\s*;", re.MULTILINE)


def parse_java(text: str) -> list[RawImport]:
    return [
        RawImport(m.group(1), "import", is_relative=False)
        for m in _JAVA_IMPORT.finditer(text)
    ]


# --------------------------------------------------------------------------- #
# Go
# --------------------------------------------------------------------------- #
_GO_IMPORT_BLOCK = re.compile(r"import\s*\((.*?)\)", re.DOTALL)
_GO_IMPORT_SINGLE = re.compile(r'^\s*import\s+(?:[\w\.]+\s+)?"([^"]+)"', re.MULTILINE)
_GO_STRING = re.compile(r'"([^"]+)"')


def parse_go(text: str) -> list[RawImport]:
    out: list[RawImport] = []
    seen: set[str] = set()

    def add(target: str) -> None:
        if target and target not in seen:
            seen.add(target)
            out.append(RawImport(target, "import", is_relative=False))

    for block in _GO_IMPORT_BLOCK.finditer(text):
        for s in _GO_STRING.finditer(block.group(1)):
            add(s.group(1))
    for m in _GO_IMPORT_SINGLE.finditer(text):
        add(m.group(1))
    return out


_PARSERS = {
    "python": parse_python,
    "javascript": parse_javascript,
    "typescript": parse_javascript,
    "c": parse_c,
    "cpp": parse_c,
    "java": parse_java,
    "go": parse_go,
}


def parse_imports(language: str, text: str) -> list[RawImport]:
    """Dispatch to the parser for ``language``; empty list if unsupported."""
    parser = _PARSERS.get(language)
    return parser(text) if parser else []
