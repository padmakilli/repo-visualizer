"""A tiny SQLite cache so a file is only summarised when its contents change.

The cache key folds in the provider and model as well as the file content
hash, so switching models produces a fresh summary while unchanged files served
by the same model are returned instantly (and for free).
"""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class CachedSummary:
    summary: str
    provider: str
    model: str
    content_hash: str
    created_at: str


def content_hash(text: str) -> str:
    """Stable SHA-256 of file content."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def make_key(provider: str, model: str, c_hash: str) -> str:
    raw = f"{provider}:{model}:{c_hash}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class SummaryCache:
    """Thread-safe-enough SQLite cache (one connection per operation)."""

    def __init__(self, db_path: str) -> None:
        self.path = Path(db_path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS summaries (
                    key          TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    path         TEXT,
                    provider     TEXT,
                    model        TEXT,
                    summary      TEXT NOT NULL,
                    created_at   TEXT NOT NULL
                )
                """
            )

    def get(self, key: str) -> CachedSummary | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT summary, provider, model, content_hash, created_at "
                "FROM summaries WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return CachedSummary(
            summary=row["summary"],
            provider=row["provider"],
            model=row["model"],
            content_hash=row["content_hash"],
            created_at=row["created_at"],
        )

    def set(
        self,
        key: str,
        *,
        content_hash: str,
        path: str,
        provider: str,
        model: str,
        summary: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO summaries
                    (key, content_hash, path, provider, model, summary, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    content_hash,
                    path,
                    provider,
                    model,
                    summary,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
