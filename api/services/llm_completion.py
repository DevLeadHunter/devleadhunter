"""
The chat completions protocol Mistral and Groq both speak (OpenAI-compatible): how a call is asked, and how its
answer, whole or streamed, is read back with what it cost.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LlmCompletion:
    """A model answer with what it cost: the text, the model, the tokens and how long it took."""

    text: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: int

    @staticmethod
    def request_payload(
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        json_mode: bool = False,
        stream: bool = False,
    ) -> dict[str, Any]:
        """
        The body of a chat completions call.

        Args:
            messages: OpenAI-style messages; ``content`` may list ``text`` / ``image_url`` parts.
            model: Model id.
            max_tokens: Answer budget.
            temperature: Sampling temperature.
            json_mode: Ask for a JSON object answer (``response_format``).
            stream: Ask for the answer as a stream of deltas.

        Returns:
            The JSON body, to which a provider adds its own options.
        """
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if stream:
            payload["stream"] = True
        return payload

    @classmethod
    def from_response(
        cls, response_payload: dict[str, Any], *, requested_model: str, started: float
    ) -> LlmCompletion | None:
        """
        Read the answer of a chat completions call.

        Args:
            response_payload: The decoded JSON answer.
            requested_model: The model asked for, kept when the answer does not name the one that served.
            started: ``time.monotonic()`` when the call started, for the latency.

        Returns:
            The completion (its text trimmed, possibly empty), or None when the answer holds no message content.
        """
        try:
            content = response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return None
        text = answer_text(content)
        if text is None:
            return None
        usage = response_payload.get("usage")
        reported: dict[str, Any] = usage if isinstance(usage, dict) else {}
        return cls(
            text=text.strip(),
            model=str(response_payload.get("model") or requested_model),
            prompt_tokens=reported.get("prompt_tokens"),
            completion_tokens=reported.get("completion_tokens"),
            latency_ms=int((time.monotonic() - started) * 1000),
        )


@dataclass
class LlmStreamUsage:
    """What a streamed call reports along the way: the served model and, on its last chunk, the token counts."""

    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


def answer_text(content: Any) -> str | None:
    """
    The text of a message content: a plain string, or the text parts of a structured content.

    Args:
        content: The ``content`` of a message or of a stream delta.

    Returns:
        The text, or None when the content is neither.
    """
    if isinstance(content, list):
        return "".join(
            str(part.get("text", "")) for part in content if isinstance(part, dict) and part.get("type") == "text"
        )
    return content if isinstance(content, str) else None


def read_chat_stream_line(line: str, usage: LlmStreamUsage | None = None) -> str | None:
    """
    The text delta of one line of a chat completions stream.

    Args:
        line: One line of the ``text/event-stream`` body.
        usage: Filled with the model and the token counts when a chunk reports them (the last one does).

    Returns:
        The delta text, or None for a blank line, the ``[DONE]`` sentinel or a chunk without text.
    """
    if not line.startswith("data:"):
        return None
    event_data = line[len("data:") :].strip()
    if not event_data or event_data == "[DONE]":
        return None
    try:
        chunk = json.loads(event_data)
    except ValueError:
        return None
    if not isinstance(chunk, dict):
        return None
    if usage is not None:
        _read_stream_usage(chunk, usage)
    try:
        content = chunk["choices"][0]["delta"].get("content")
    except (KeyError, IndexError, TypeError, AttributeError):
        return None
    delta = answer_text(content)
    return delta or None


def _read_stream_usage(chunk: dict[str, Any], usage: LlmStreamUsage) -> None:
    """Keep the model and the tokens a chunk reports (Groq puts its usage under ``x_groq``)."""
    if isinstance(chunk.get("model"), str) and chunk["model"]:
        usage.model = chunk["model"]
    reported = chunk.get("usage")
    if not isinstance(reported, dict):
        extra = chunk.get("x_groq")
        reported = extra.get("usage") if isinstance(extra, dict) else None
    if not isinstance(reported, dict):
        return
    if isinstance(reported.get("prompt_tokens"), int):
        usage.prompt_tokens = reported["prompt_tokens"]
    if isinstance(reported.get("completion_tokens"), int):
        usage.completion_tokens = reported["completion_tokens"]
