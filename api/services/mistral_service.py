"""
Mistral La Plateforme client (OpenAI-compatible chat completions), used by the AI assistant module.

The assistant's calls go to Mistral first (``services/ai_assistant/llm_router.py``); the rest of the
product stays on Groq. A failed call returns None so the router can fall back — or not, for an
assistant flagged « EU only ». A request Mistral rejects as malformed raises instead: that is our
call being wrong, not Mistral being down.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from core.config import settings
from services.llm_service import LlmCompletion, LlmStreamUsage, read_chat_stream_line

logger = logging.getLogger(__name__)

_MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
# Statuses worth one more try (rate limit, transient server errors), and the longest wait between tries.
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
_MAX_RETRY_DELAY_SECONDS = 3.0
# The request itself is wrong (e.g. a conversation that does not end on the visitor): not an outage.
_REJECTED_STATUSES = frozenset({400, 422})


class MistralRequestRejectedError(Exception):
    """Mistral refused the request itself (HTTP 400 / 422): the call is wrong, Mistral is not down."""


class MistralService:
    """Thin Mistral client: failures reported as None (the caller decides), optional quick retries."""

    @property
    def is_configured(self) -> bool:
        """True when a Mistral API key is available."""
        return bool(settings.mistral_api_key)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_tokens: int = 600,
        temperature: float = 0.5,
        json_mode: bool = False,
        timeout: float = 30.0,
        retries: int = 0,
    ) -> LlmCompletion | None:
        """
        Call Mistral chat completions.

        Args:
            messages: OpenAI-style messages; ``content`` may list ``text`` / ``image_url`` parts.
            model: Mistral model id.
            max_tokens: Answer budget.
            temperature: Sampling temperature.
            json_mode: Ask for a JSON object answer (``response_format``).
            timeout: HTTP timeout in seconds, per attempt.
            retries: Extra attempts after a rate limit or a transient server error (0 when a fallback
                is faster than waiting).

        Returns:
            The completion, or None when Mistral is off or the call failed.

        Raises:
            MistralRequestRejectedError: Mistral rejected the request as malformed (HTTP 400 / 422).
        """
        if not self.is_configured:
            return None
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                data = await self._post(client, payload, retries=retries)
        except MistralRequestRejectedError:
            raise
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Mistral call failed (%s): HTTP %s %s", model, exc.response.status_code, exc.response.text[:300]
            )
            return None
        except Exception as exc:
            logger.warning("Mistral call failed (%s): %s", model, exc)
            return None
        text = self._text(data)
        if text is None:
            logger.warning("Mistral answer without content (%s)", model)
            return None
        usage: dict[str, Any] = data.get("usage") or {}
        return LlmCompletion(
            text=text,
            model=str(data.get("model") or model),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    async def complete_stream(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_tokens: int = 600,
        temperature: float = 0.5,
        timeout: float = 30.0,
        retries: int = 0,
        usage: LlmStreamUsage | None = None,
    ) -> AsyncIterator[str]:
        """
        Call Mistral chat completions as a stream, one text delta at a time.

        A failure before the first delta ends the stream empty (the caller decides, as with a None of
        ``complete``); a failure after it ends the stream on what came through, since a reader already has it.

        Args:
            messages: OpenAI-style messages.
            model: Mistral model id.
            max_tokens: Answer budget.
            temperature: Sampling temperature.
            timeout: HTTP timeout in seconds (between two chunks once the stream is open).
            retries: Extra attempts after a rate limit or a transient server error.
            usage: Filled with the served model and the token counts Mistral reports on its last chunk.

        Yields:
            The text deltas, in order.

        Raises:
            MistralRequestRejectedError: Mistral rejected the request as malformed (HTTP 400 / 422).
        """
        if not self.is_configured:
            return
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        headers = {"Authorization": f"Bearer {settings.mistral_api_key}"}
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                attempt = 0
                while True:
                    async with client.stream("POST", _MISTRAL_URL, headers=headers, json=payload) as response:
                        if response.status_code in _REJECTED_STATUSES:
                            body = (await response.aread()).decode(errors="replace")[:300]
                            logger.warning("Mistral rejected the request (%s): %s", response.status_code, body)
                            raise MistralRequestRejectedError(body)
                        if response.status_code in _RETRYABLE_STATUSES and attempt < retries:
                            attempt += 1
                            await asyncio.sleep(self._retry_delay_seconds(response))
                            continue
                        if response.status_code >= 400:
                            await response.aread()  # the error text is worth logging
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            delta = read_chat_stream_line(line, usage)
                            if delta:
                                yield delta
                        return
        except MistralRequestRejectedError:
            raise
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Mistral stream failed (%s): HTTP %s %s", model, exc.response.status_code, exc.response.text[:300]
            )
        except Exception as exc:
            logger.warning("Mistral stream failed (%s): %s", model, exc)

    async def _post(self, client: httpx.AsyncClient, payload: dict[str, Any], *, retries: int) -> dict[str, Any]:
        """POST a completion, retrying a rate limit or a transient error up to ``retries`` times."""
        attempt = 0
        while True:
            response = await client.post(
                _MISTRAL_URL, headers={"Authorization": f"Bearer {settings.mistral_api_key}"}, json=payload
            )
            if response.status_code in _REJECTED_STATUSES:
                logger.warning("Mistral rejected the request (%s): %s", response.status_code, response.text[:300])
                raise MistralRequestRejectedError(response.text[:300])
            if response.status_code in _RETRYABLE_STATUSES and attempt < retries:
                attempt += 1
                await asyncio.sleep(self._retry_delay_seconds(response))
                continue
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _retry_delay_seconds(response: httpx.Response) -> float:
        """The server's ``retry-after`` when given (capped), else one second."""
        try:
            delay = float(response.headers.get("retry-after", "1"))
        except ValueError:
            delay = 1.0
        return max(0.0, min(delay, _MAX_RETRY_DELAY_SECONDS))

    @staticmethod
    def _text(data: dict[str, Any]) -> str | None:
        """The answer text: a plain string, or the text chunks of a structured content."""
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return None
        if isinstance(content, list):
            content = "".join(
                str(chunk.get("text", ""))
                for chunk in content
                if isinstance(chunk, dict) and chunk.get("type") == "text"
            )
        return content.strip() if isinstance(content, str) and content.strip() else None


mistral_service = MistralService()
