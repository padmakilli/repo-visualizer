"""Pydantic schemas for API requests and responses."""
from __future__ import annotations

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Graph payload
# --------------------------------------------------------------------------- #
class GraphNode(BaseModel):
    """A single file in the dependency graph."""

    id: str = Field(..., description="Repo-relative path, used as a stable id.")
    label: str = Field(..., description="File name shown on the node.")
    path: str = Field(..., description="Repo-relative path.")
    dir: str = Field("", description="Parent directory (repo-relative).")
    language: str = Field("unknown", description="Detected language.")
    loc: int = Field(0, description="Total lines.")
    sloc: int = Field(0, description="Source lines (no blanks/comments).")
    complexity: int = Field(0, description="Approx. cyclomatic complexity.")
    size_bytes: int = Field(0, description="File size in bytes.")
    in_degree: int = Field(0, description="Number of files importing this one.")
    out_degree: int = Field(0, description="Number of files this one imports.")


class GraphEdge(BaseModel):
    """A directed dependency: ``source`` imports ``target``."""

    id: str
    source: str
    target: str
    kind: str = Field("import", description="import | include | require ...")


class GraphStats(BaseModel):
    root: str
    file_count: int
    edge_count: int
    total_loc: int
    languages: dict[str, int] = Field(default_factory=dict)
    skipped: int = 0


class GraphResponse(BaseModel):
    root: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    stats: GraphStats


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #
class AnalyzeRequest(BaseModel):
    path: str = Field(..., description="Absolute or ~-relative path to a local repo.")
    include_external: bool = Field(
        False, description="Reserved: also emit nodes for third-party modules."
    )


class ExplainRequest(BaseModel):
    root: str = Field(..., description="The analyzed repo root.")
    path: str = Field(..., description="Repo-relative file path to explain.")
    force: bool = Field(False, description="Bypass cache and re-summarize.")


class FileRequest(BaseModel):
    root: str
    path: str


# --------------------------------------------------------------------------- #
# Responses
# --------------------------------------------------------------------------- #
class ExplainResponse(BaseModel):
    path: str
    summary: str
    cached: bool
    model: str
    provider: str


class FileResponse(BaseModel):
    path: str
    language: str
    loc: int
    sloc: int
    complexity: int
    size_bytes: int
    truncated: bool
    content: str
    imports: list[str] = Field(default_factory=list)
