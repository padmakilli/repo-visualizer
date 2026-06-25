"""Provider adapters that turn source code into a short plain-English summary.

All providers talk to their REST endpoints via ``httpx`` so no vendor SDK is
strictly required. A ``NullProvider`` keeps the app fully functional when no
API key is configured.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from ..config import Settings

# Keep prompt cost bounded regardless of file size.
_MAX_CODE_CHARS = 12_000

_SYSTEM_PROMPT = (
    "You are a senior engineer helping a teammate onboard to an unfamiliar "
    "codebase. Explain what a source file does in exactly three short, plain-"
    "English sentences. Sentence 1: the file's overall purpose. Sentence 2: its "
    "key responsibilities or main pieces. Sentence 3: how it fits with the rest "
    "of the project. Avoid restating the code line by line and avoid jargon."
)


def _build_user_prompt(path: str, language: str, code: str) -> str:
    snippet = code[:_MAX_CODE_CHARS]
    if len(code) > _MAX_CODE_CHARS:
        snippet += "\n\n/* ...truncated for length... */"
    return (
        f"File: {path}\nLanguage: {language}\n\n"
        f"Source:\n```{language}\n{snippet}\n```\n\n"
        "Explain what this code does in 3 simple sentences."
    )


class AIError(RuntimeError):
    """Raised when a provider call fails."""


class Provider(ABC):
    name: str = "none"

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    def summarize(self, path: str, language: str, code: str) -> str:  # pragma: no cover
        ...


class NullProvider(Provider):
    name = "none"

    def __init__(self) -> None:
        super().__init__(model="none")

    def summarize(self, path: str, language: str, code: str) -> str:
        return (
            "AI summaries are not configured. Set AI_PROVIDER and the matching "
            "API key in backend/.env to enable plain-English file explanations."
        )


class AnthropicProvider(Provider):
    name = "anthropic"
    _URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str) -> None:
        super().__init__(model)
        self._api_key = api_key

    def summarize(self, path: str, language: str, code: str) -> str:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": self.model,
            "max_tokens": 300,
            "system": _SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": _build_user_prompt(path, language, code)}
            ],
        }
        try:
            resp = httpx.post(self._URL, headers=headers, json=body, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise AIError(f"Anthropic request failed: {exc}") from exc
        blocks = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
        text = "".join(blocks).strip()
        if not text:
            raise AIError("Anthropic returned an empty response.")
        return text


class OpenAIProvider(Provider):
    name = "openai"
    _URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str) -> None:
        super().__init__(model)
        self._api_key = api_key

    def summarize(self, path: str, language: str, code: str) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "max_tokens": 300,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(path, language, code)},
            ],
        }
        try:
            resp = httpx.post(self._URL, headers=headers, json=body, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise AIError(f"OpenAI request failed: {exc}") from exc
        try:
            text = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise AIError("Unexpected OpenAI response shape.") from exc
        if not text:
            raise AIError("OpenAI returned an empty response.")
        return text


class GeminiProvider(Provider):
    name = "gemini"
    _BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, model: str) -> None:
        super().__init__(model)
        self._api_key = api_key

    def summarize(self, path: str, language: str, code: str) -> str:
        url = f"{self._BASE}/{self.model}:generateContent?key={self._api_key}"
        body = {
            "systemInstruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
            "contents": [
                {"parts": [{"text": _build_user_prompt(path, language, code)}]}
            ],
            "generationConfig": {"maxOutputTokens": 300},
        }
        try:
            resp = httpx.post(url, json=body, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            raise AIError(f"Gemini request failed: {exc}") from exc
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts).strip()
        except (KeyError, IndexError) as exc:
            raise AIError("Unexpected Gemini response shape.") from exc
        if not text:
            raise AIError("Gemini returned an empty response.")
        return text


def get_provider(settings: Settings) -> Provider:
    """Construct the provider selected in settings, falling back to Null."""
    provider = (settings.ai_provider or "none").lower()
    if provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model)
    if provider == "openai" and settings.openai_api_key:
        return OpenAIProvider(settings.openai_api_key, settings.openai_model)
    if provider == "gemini" and settings.gemini_api_key:
        return GeminiProvider(settings.gemini_api_key, settings.gemini_model)
    return NullProvider()
