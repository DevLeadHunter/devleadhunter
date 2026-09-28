"""The chat completions protocol shared by Mistral and Groq: the request body, and the answer read back."""

import asyncio
import json
import time
from typing import Any

import httpx
import pytest

import services.llm_service as llm_module
from services.llm_completion import LlmCompletion
from services.llm_service import LLMService

_MESSAGES: list[dict[str, Any]] = [{"role": "user", "content": "Bonjour"}]


def test_the_request_body_asks_json_or_a_stream_only_when_told() -> None:
    plain = LlmCompletion.request_payload(_MESSAGES, model="m", max_tokens=300, temperature=0.2)
    json_answer = LlmCompletion.request_payload(_MESSAGES, model="m", max_tokens=300, temperature=0.2, json_mode=True)
    streamed = LlmCompletion.request_payload(_MESSAGES, model="m", max_tokens=300, temperature=0.2, stream=True)

    assert plain == {"model": "m", "messages": _MESSAGES, "temperature": 0.2, "max_tokens": 300}
    assert json_answer["response_format"] == {"type": "json_object"} and "stream" not in json_answer
    assert streamed["stream"] is True and "response_format" not in streamed


def test_the_answer_reads_a_plain_or_a_structured_content_with_its_cost() -> None:
    started = time.monotonic()
    plain = LlmCompletion.from_response(
        {
            "model": "served-model",
            "choices": [{"message": {"content": "  Bonjour !  "}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 3},
        },
        requested_model="asked-model",
        started=started,
    )
    structured = LlmCompletion.from_response(
        {"choices": [{"message": {"content": [{"type": "text", "text": "Bon"}, {"type": "text", "text": "jour"}]}}]},
        requested_model="asked-model",
        started=started,
    )

    assert plain is not None and (plain.text, plain.model) == ("Bonjour !", "served-model")
    assert (plain.prompt_tokens, plain.completion_tokens) == (12, 3)
    assert structured is not None and (structured.text, structured.model) == ("Bonjour", "asked-model")
    assert (structured.prompt_tokens, structured.completion_tokens) == (None, None)


def test_an_answer_without_a_message_content_is_none() -> None:
    started = time.monotonic()

    assert LlmCompletion.from_response({"choices": []}, requested_model="m", started=started) is None
    assert LlmCompletion.from_response({"error": "boom"}, requested_model="m", started=started) is None
    assert (
        LlmCompletion.from_response({"choices": [{"message": {"content": None}}]}, requested_model="m", started=started)
        is None
    )


def _groq_with(handler: Any, monkeypatch: pytest.MonkeyPatch) -> LLMService:
    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def patched_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(llm_module.httpx, "AsyncClient", patched_client)
    monkeypatch.setattr(llm_module.settings, "groq_api_key", "groq-key")
    return LLMService()


def test_the_groq_client_floors_the_budget_of_a_reasoning_model_and_reads_the_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "openai/gpt-oss-120b",
                "choices": [{"message": {"content": "interested"}}],
                "usage": {"prompt_tokens": 90, "completion_tokens": 7},
            },
        )

    completion = asyncio.run(
        _groq_with(handler, monkeypatch).complete(_MESSAGES, model="openai/gpt-oss-120b", max_tokens=10)
    )

    assert completion is not None and completion.text == "interested"
    assert (completion.prompt_tokens, completion.completion_tokens) == (90, 7)
    assert bodies[0]["max_tokens"] == 512 and bodies[0]["reasoning_effort"] == "low"


def test_a_groq_answer_without_content_is_no_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {}}]})

    assert asyncio.run(_groq_with(handler, monkeypatch).complete(_MESSAGES)) is None
