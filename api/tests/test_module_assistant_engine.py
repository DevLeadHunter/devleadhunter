"""The conversation engine of a module's assistant: tools called by Claude, answers kept to what they read."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import pytest
from sqlalchemy.orm import Session

from schemas.module_assistant import AssistantBar, AssistantChart, AssistantPastExchange
from services.module_assistant_engine import (
    AssistantOutcome,
    AssistantTool,
    AssistantToolArguments,
    AssistantToolResult,
    ModuleAssistantEngine,
)


def _count_tool(calls: list[AssistantToolArguments]) -> AssistantTool:
    """A tool that counts 12 records and draws them, noting the arguments it was called with."""

    def run(_db: Session, _user_id: int, arguments: AssistantToolArguments) -> AssistantToolResult:
        calls.append(arguments)
        return AssistantToolResult(
            facts={"count": 12, "town": arguments.get("town")},
            sentence="12 fiches trouvées.",
            cards=["first", "second"],
            chart=AssistantChart(title="Fiches", bars=[AssistantBar(label="Nantes", value=12)]),
        )

    return AssistantTool(
        name="count_records", description="Compte les fiches.", run=run, parameters={"town": {"type": "string"}}
    )


def tool_call(name: str, arguments: dict[str, Any], call_id: str = "call_1") -> SimpleNamespace:
    """A message of Claude that calls one tool."""
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[SimpleNamespace(type="tool_use", id=call_id, name=name, input=arguments)],
    )


def final_answer(
    answer: str, next_questions: list[Any] | None = None, *, needs_no_data: bool = False
) -> SimpleNamespace:
    """A final message of Claude, in the JSON format the engine asks for."""
    text: str = json.dumps(
        {"answer": answer, "next_questions": next_questions or [], "needs_no_data": needs_no_data}, ensure_ascii=False
    )
    return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)])


def claude_saying(monkeypatch: pytest.MonkeyPatch, replies: list[Any]) -> list[dict[str, Any]]:
    """
    Make Claude give these messages in order (an exception is raised instead); the requests are returned.

    Each request is kept as it was when it left: the engine goes on adding to its list of messages.
    """
    received: list[dict[str, Any]] = []

    async def create_message(_self: ModuleAssistantEngine, **request: Any) -> Any:
        received.append({**request, "messages": list(request["messages"])})
        reply: Any = replies[len(received) - 1] if len(received) <= len(replies) else None
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(ModuleAssistantEngine, "is_available", property(lambda _self: True))
    monkeypatch.setattr(ModuleAssistantEngine, "_create_message", create_message)
    return received


def _answer(
    db: Session, tool: AssistantTool, question: str, history: list[AssistantPastExchange] | None = None
) -> AssistantOutcome | None:
    """Ask the engine a question with one tool."""
    return asyncio.run(
        ModuleAssistantEngine().answer(
            db, 1, subject="Des fiches.", tools=[tool], question=question, history=history or []
        )
    )


def test_claude_calls_a_tool_then_answers_from_its_facts(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[AssistantToolArguments] = []
    received = claude_saying(
        monkeypatch,
        [
            tool_call("count_records", {"town": "Nantes"}),
            final_answer("Vous avez 12 fiches à Nantes.", ["Et à Rennes ?", 4, "x" * 200]),
        ],
    )

    outcome = _answer(db, _count_tool(calls), "Combien de fiches à Nantes ?")

    assert outcome is not None
    assert calls == [{"town": "Nantes"}]
    assert outcome.text == "Vous avez 12 fiches à Nantes."
    assert (list(outcome.cards), outcome.next_questions) == (["first", "second"], ["Et à Rennes ?"])
    assert outcome.chart is not None and outcome.chart.title == "Fiches"
    assert 'count_records({"town": "Nantes"})' in outcome.context
    tool_result: dict[str, Any] = received[1]["messages"][-1]["content"][0]
    assert (tool_result["type"], tool_result["tool_use_id"]) == ("tool_result", "call_1")
    assert received[0]["tools"][0]["input_schema"]["properties"] == {"town": {"type": "string"}}


def test_an_answer_stating_a_number_no_tool_gave_is_replaced(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    claude_saying(monkeypatch, [tool_call("count_records", {}), final_answer("Vous avez 48 fiches, dont 12 à Nantes.")])

    outcome = _answer(db, _count_tool([]), "Combien de fiches ?")

    assert outcome is not None and outcome.text == "12 fiches trouvées."


def test_the_conversation_so_far_is_handed_to_claude(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    received = claude_saying(monkeypatch, [tool_call("count_records", {"town": "Rennes"}), final_answer("12.")])

    _answer(
        db,
        _count_tool([]),
        "Et ailleurs ?",
        [AssistantPastExchange(question="Combien ici ?", answer="12 fiches ici.", context="count_records -> 12")],
    )

    first_messages: list[dict[str, Any]] = received[0]["messages"]
    assert [message["role"] for message in first_messages] == ["user", "assistant", "user"]
    assert first_messages[0]["content"] == "Combien ici ?"
    assert "count_records -> 12" in first_messages[1]["content"]


def test_an_answer_written_without_reading_is_sent_back_to_the_tools(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[AssistantToolArguments] = []
    received = claude_saying(
        monkeypatch,
        [final_answer("Vous en avez beaucoup."), tool_call("count_records", {}), final_answer("12 fiches.")],
    )

    outcome = _answer(db, _count_tool(calls), "Combien de fiches ?")

    assert outcome is not None and outcome.text == "12 fiches."
    assert (len(calls), len(received)) == (1, 3)


def test_an_answer_that_needs_no_data_is_kept_once_claude_says_so(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    claude_saying(monkeypatch, [final_answer("Bonjour."), final_answer("Bonjour.", needs_no_data=True)])

    outcome = _answer(db, _count_tool([]), "Bonjour")

    assert outcome is not None and (outcome.text, list(outcome.cards)) == ("Bonjour.", [])


def test_an_answer_that_insists_without_reading_leaves_the_module_answer(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    claude_saying(monkeypatch, [final_answer("Beaucoup."), final_answer("Vraiment beaucoup.")])

    assert _answer(db, _count_tool([]), "Combien de fiches ?") is None


def test_a_tool_that_fails_is_told_to_claude_as_an_error(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    def run(_db: Session, _user_id: int, _arguments: AssistantToolArguments) -> AssistantToolResult:
        raise RuntimeError("no such table")

    received = claude_saying(
        monkeypatch,
        [tool_call("count_records", {}), final_answer("Cette information n’est pas disponible.", needs_no_data=True)],
    )

    outcome = _answer(db, AssistantTool(name="count_records", description="Compte.", run=run), "Combien ?")

    assert received[1]["messages"][-1]["content"][0]["is_error"] is True
    assert outcome is None


def test_several_tools_called_at_once_are_answered_in_one_message(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[AssistantToolArguments] = []
    both: SimpleNamespace = SimpleNamespace(
        stop_reason="tool_use",
        content=[
            SimpleNamespace(type="tool_use", id="call_1", name="count_records", input={"town": "Nantes"}),
            SimpleNamespace(type="tool_use", id="call_2", name="count_records", input={"town": "Rennes"}),
        ],
    )
    received = claude_saying(monkeypatch, [both, final_answer("12 fiches dans chaque ville.")])

    outcome = _answer(db, _count_tool(calls), "Nantes ou Rennes ?")

    assert outcome is not None and len(calls) == 2
    assert [block["tool_use_id"] for block in received[1]["messages"][-1]["content"]] == ["call_1", "call_2"]


def test_claude_refusing_or_failing_leaves_the_module_answer(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    request: httpx2.Request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    overloaded: anthropic.APIStatusError = anthropic.APIStatusError(
        "overloaded", response=httpx2.Response(529, request=request), body=None
    )
    claude_saying(monkeypatch, [overloaded])
    assert _answer(db, _count_tool([]), "Combien de fiches ?") is None

    claude_saying(monkeypatch, [SimpleNamespace(stop_reason="refusal", content=[])])
    assert _answer(db, _count_tool([]), "Combien de fiches ?") is None


def test_claude_that_never_stops_calling_tools_is_stopped(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    claude_saying(monkeypatch, [tool_call("count_records", {})] * 20)
    calls: list[AssistantToolArguments] = []

    outcome = _answer(db, _count_tool(calls), "Combien de fiches ?")

    assert len(calls) == ModuleAssistantEngine.MAXIMUM_TOOL_CALLS
    assert outcome is not None and outcome.text.startswith("12 fiches trouvées.")


def test_no_key_leaves_the_module_answer(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ModuleAssistantEngine, "is_available", property(lambda _self: False))

    assert _answer(db, _count_tool([]), "Combien de fiches ?") is None


def test_an_answer_with_a_number_of_its_own_is_asked_again_once(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    received = claude_saying(
        monkeypatch,
        [tool_call("count_records", {}), final_answer("12 fiches, soit 88 de moins."), final_answer("12 fiches.")],
    )

    outcome = _answer(db, _count_tool([]), "Combien de fiches ?")

    assert outcome is not None and outcome.text == "12 fiches."
    assert len(received) == 3


def test_two_searches_of_one_turn_draw_the_cards_of_both(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    def run(_db: Session, _user_id: int, arguments: AssistantToolArguments) -> AssistantToolResult:
        return AssistantToolResult(facts={}, sentence="1 fiche.", cards=[str(arguments.get("town"))])

    both: SimpleNamespace = SimpleNamespace(
        stop_reason="tool_use",
        content=[
            SimpleNamespace(type="tool_use", id="call_1", name="count_records", input={"town": "Nantes"}),
            SimpleNamespace(type="tool_use", id="call_2", name="count_records", input={"town": "Rennes"}),
        ],
    )
    claude_saying(monkeypatch, [both, final_answer("Une fiche dans chaque ville.")])

    outcome = _answer(db, AssistantTool(name="count_records", description="Compte.", run=run), "Nantes ou Rennes ?")

    assert outcome is not None and list(outcome.cards) == ["Nantes", "Rennes"]
