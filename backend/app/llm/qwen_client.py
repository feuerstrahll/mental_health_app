from __future__ import annotations

import json
import logging
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)


class ModelClientError(RuntimeError):
    """Base exception for model client failures."""

    def __init__(self, reason: str, detail: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


class ModelTimeoutError(ModelClientError):
    """Raised when model call timed out."""


class ModelDisabledError(ModelClientError):
    """Raised when model is disabled by config."""


class ModelClient(Protocol):
    async def generate_chat(self, *, messages: list[dict[str, str]], timeout_seconds: float | None = None) -> str:
        ...


class OpenAICompatibleQwenClient:
    """OpenAI-compatible client for self-hosted Qwen (vLLM/FastAPI compatible)."""

    def __init__(
        self,
        *,
        enabled: bool,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout_seconds: float = 10.0,
        temperature: float = 0.35,
        max_tokens: int | None = None,
        max_completion_tokens: int | None = None,
        max_retries: int = 1,
    ) -> None:
        self._enabled = enabled
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._temperature = temperature
        self._max_completion_tokens = max_completion_tokens if max_completion_tokens is not None else max_tokens
        self._max_retries = max(0, max_retries)

    async def generate_chat(self, *, messages: list[dict[str, str]], timeout_seconds: float | None = None) -> str:
        if not self._enabled:
            raise ModelDisabledError("qwen_disabled")

        endpoint = f"{self._base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "stream": False,
        }
        if self._max_completion_tokens is not None:
            payload["max_tokens"] = self._max_completion_tokens
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        last_error: ModelClientError | None = None
        raw = ""
        request_timeout = timeout_seconds if timeout_seconds is not None else self._timeout_seconds
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=request_timeout) as client:
                    response = await client.post(endpoint, json=payload, headers=headers)
            except httpx.TimeoutException as exc:
                logger.warning("qwen_timeout attempt=%d", attempt + 1)
                last_error = ModelTimeoutError("model_timeout")
                if attempt < self._max_retries:
                    continue
                raise last_error from exc
            except httpx.RequestError as exc:
                logger.warning("qwen_connection_error attempt=%d error=%s", attempt + 1, exc.__class__.__name__)
                last_error = ModelClientError("model_connection_error", detail=exc.__class__.__name__)
                if attempt < self._max_retries:
                    continue
                raise last_error from exc

            if response.status_code >= 500:
                detail = self._safe_detail(response.text)
                logger.warning(
                    "qwen_http_error status=%d attempt=%d detail=%s",
                    response.status_code,
                    attempt + 1,
                    detail,
                )
                last_error = ModelClientError(
                    "model_http_error",
                    detail=f"{response.status_code}:{detail}",
                )
                if attempt < self._max_retries:
                    continue
                raise last_error
            if response.status_code >= 400:
                detail = self._safe_detail(response.text)
                logger.warning("qwen_http_error status=%d detail=%s", response.status_code, detail)
                raise ModelClientError(
                    "model_http_error",
                    detail=f"{response.status_code}:{detail}",
                )

            raw = response.text
            break
        else:
            raise last_error or ModelClientError("model_connection_error")

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ModelClientError("invalid_model_json") from exc

        content = self._extract_content(parsed)
        if not content:
            raise ModelClientError("empty_model_content")
        return content.strip()

    def _safe_detail(self, value: str | None) -> str:
        if not value:
            return ""
        return " ".join(value.strip().split())[:180]

    def _extract_content(self, payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""

        message = first.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_value = item.get("text")
                        if isinstance(text_value, str):
                            parts.append(text_value)
                return "\n".join(parts).strip()

        text = first.get("text")
        if isinstance(text, str):
            return text
        return ""


class QwenClient(OpenAICompatibleQwenClient):
    """Backward-compatible alias for older wiring."""

    async def compose(self, prompt: str) -> str | None:
        if not self._enabled:
            return None
        try:
            return await self.generate_chat(
                messages=[{"role": "user", "content": prompt}],
                timeout_seconds=8.0,
            )
        except ModelClientError:
            return None
