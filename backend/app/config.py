"""Application configuration loaded from environment / .env file."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings.

    Values come from environment variables or a local ``.env`` file. See
    ``.env.example`` for documentation of each field.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AI provider
    ai_provider: str = "none"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5"
    openai_model: str = "gpt-4o-mini"
    gemini_model: str = "gemini-1.5-flash"

    # Analysis
    repo_root: str | None = None
    max_file_bytes: int = 1_000_000
    cache_db: str = "./.cache/summaries.db"

    # CORS (comma separated)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def repo_root_path(self) -> Path | None:
        return Path(self.repo_root).expanduser().resolve() if self.repo_root else None


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
