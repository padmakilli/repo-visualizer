"""High-level file explanation: cache lookup, then provider call on a miss."""
from __future__ import annotations

from ..config import Settings
from ..models import ExplainResponse
from .cache import SummaryCache, content_hash, make_key
from .providers import Provider, get_provider


class Summarizer:
    """Explain files in plain English, caching by content hash."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._provider: Provider = get_provider(settings)
        self._cache = SummaryCache(settings.cache_db)

    @property
    def provider_name(self) -> str:
        return self._provider.name

    def explain(
        self,
        *,
        rel_path: str,
        language: str,
        code: str,
        force: bool = False,
    ) -> ExplainResponse:
        c_hash = content_hash(code)
        key = make_key(self._provider.name, self._provider.model, c_hash)

        if not force:
            cached = self._cache.get(key)
            if cached is not None:
                return ExplainResponse(
                    path=rel_path,
                    summary=cached.summary,
                    cached=True,
                    model=cached.model,
                    provider=cached.provider,
                )

        summary = self._provider.summarize(rel_path, language, code)

        # Only persist real summaries (the Null provider returns guidance text).
        if self._provider.name != "none":
            self._cache.set(
                key,
                content_hash=c_hash,
                path=rel_path,
                provider=self._provider.name,
                model=self._provider.model,
                summary=summary,
            )

        return ExplainResponse(
            path=rel_path,
            summary=summary,
            cached=False,
            model=self._provider.model,
            provider=self._provider.name,
        )
