"""REST endpoints: analyse a repo, explain a file, fetch file detail."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..ai.providers import AIError
from ..analyzer.dependency_parser import parse_imports
from ..analyzer.graph_builder import build_graph, read_text
from ..analyzer.languages import detect_language
from ..analyzer.metrics import compute_metrics
from ..config import get_settings
from ..models import (
    AnalyzeRequest,
    ExplainRequest,
    ExplainResponse,
    FileRequest,
    FileResponse,
    GraphResponse,
)
from ..paths import PathError, resolve_file, validate_root

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "ai_provider": settings.ai_provider,
        "sandbox": str(settings.repo_root_path) if settings.repo_root_path else None,
    }


@router.post("/analyze", response_model=GraphResponse)
def analyze(req: AnalyzeRequest, request: Request) -> GraphResponse:
    settings = get_settings()
    try:
        root = validate_root(req.path, settings)
    except PathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    graph = build_graph(root, settings.max_file_bytes)
    # Remember this root so subsequent file/explain calls are permitted.
    request.app.state.analyzed_roots.add(str(root))
    return graph


@router.post("/file", response_model=FileResponse)
def file_detail(req: FileRequest, request: Request) -> FileResponse:
    settings = get_settings()
    try:
        _, target = resolve_file(
            req.root, req.path, settings, request.app.state.analyzed_roots
        )
    except PathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    language = detect_language(target)
    text, truncated = read_text(target, settings.max_file_bytes)
    metrics = compute_metrics(text, language) if text else compute_metrics("", language)
    imports = [imp.target for imp in parse_imports(language, text)] if text else []

    return FileResponse(
        path=req.path,
        language=language,
        loc=metrics.loc,
        sloc=metrics.sloc,
        complexity=metrics.complexity,
        size_bytes=target.stat().st_size,
        truncated=truncated,
        content=text,
        imports=imports,
    )


@router.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest, request: Request) -> ExplainResponse:
    settings = get_settings()
    try:
        _, target = resolve_file(
            req.root, req.path, settings, request.app.state.analyzed_roots
        )
    except PathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    language = detect_language(target)
    text, _ = read_text(target, settings.max_file_bytes)
    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty or unreadable.")

    try:
        return request.app.state.summarizer.explain(
            rel_path=req.path,
            language=language,
            code=text,
            force=req.force,
        )
    except AIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
