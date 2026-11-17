"""
The conversation engine of a product module's assistant.

Claude reads the owner's question with the conversation so far, then calls the tools the module offers: each tool
reads the module's own data and hands back facts. Claude may chain several tools before it writes its answer. What
the page draws (cards, chart, highlight) always comes from the tools, never from the model, and an answer that states
a number no tool gave is replaced by the sentences the tools wrote themselves.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar

import anthropic
from sqlalchemy.orm import Session

from core.config import settings
from schemas.module_assistant import AssistantChart, AssistantHighlight, AssistantPastExchange

logger = logging.getLogger(__name__)

AssistantToolArguments = dict[str, object]


class AssistantArgumentReader:
    """Reads the arguments the model handed a tool: a value of the wrong kind or out of bounds is dropped."""

    @staticmethod
    def whole_number(arguments: AssistantToolArguments, key: str, *, lowest: int, highest: int) -> int | None:
        """
        A whole number between two bounds.

        Args:
            arguments: What the model gave.
            key: The argument to read.
            lowest: The smallest value kept.
            highest: The largest value kept.

        Returns:
            The number, None when it is missing, not a whole number, or out of the bounds.
        """
        value: object = arguments.get(key)
        if isinstance(value, bool) or not isinstance(value, int | float) or value != int(value):
            return None
        number: int = int(value)
        return number if lowest <= number <= highest else None

    @staticmethod
    def words(arguments: AssistantToolArguments, key: str, *, longest: int) -> str | None:
        """
        A short text.

        Args:
            arguments: What the model gave.
            key: The argument to read.
            longest: The longest text kept.

        Returns:
            The text without the spaces around it, None when it is missing, empty or too long.
        """
        value: object = arguments.get(key)
        if not isinstance(value, str) or not 0 < len(value.strip()) <= longest:
            return None
        return value.strip()

    @staticmethod
    def choice(arguments: AssistantToolArguments, key: str, choices: Sequence[str], *, default: str) -> str:
        """
        One value of a closed list.

        Args:
            arguments: What the model gave.
            key: The argument to read.
            choices: The values the tool knows.
            default: The value of a missing or unknown choice.

        Returns:
            The choice.
        """
        value: object = arguments.get(key)
        return value if isinstance(value, str) and value in choices else default


@dataclass(frozen=True)
class AssistantToolResult:
    """
    What a tool read from the module's data.

    Attributes:
        facts: What the model reads to write its answer.
        sentence: The same result in one sentence, written without the model.
        cards: The module's records to draw, as the module's own card schema.
        chart: A chart to draw, None when the result has none.
        highlight: One thing to look at first, None when there is none.
        is_selection: Whether the cards are a choice the model made: they then stand alone, in their order, in place
            of the cards an earlier call of the turn found.
    """

    facts: dict[str, object]
    sentence: str
    cards: Sequence[object] = ()
    chart: AssistantChart | None = None
    highlight: AssistantHighlight | None = None
    is_selection: bool = False


@dataclass(frozen=True)
class AssistantTool:
    """
    One way of reading the module's data, offered to the model.

    Attributes:
        name: The name the model calls it by.
        description: What it reads and when to call it, as the model reads it.
        run: Reads the data of one owner with the arguments the model gave.
        parameters: Its arguments as JSON Schema properties, all optional; the tool itself drops a value it cannot use.
    """

    name: str
    description: str
    run: Callable[[Session, int, AssistantToolArguments], AssistantToolResult]
    parameters: dict[str, dict[str, object]] = field(default_factory=dict[str, dict[str, object]])


@dataclass(frozen=True)
class AssistantOutcome:
    """
    The answer to a question.

    Attributes:
        text: The answer in words.
        cards: The records to draw, those of the last tool that found some.
        chart: The chart of the last tool that drew one.
        highlight: The highlight of the last tool that gave one.
        next_questions: Questions the model offers to carry on with.
        context: What the tools read, in short: the page sends it back with the next question, so « the first
            one » or « and in Nantes? » still means something.
    """

    text: str
    cards: Sequence[object] = ()
    chart: AssistantChart | None = None
    highlight: AssistantHighlight | None = None
    next_questions: list[str] = field(default_factory=list[str])
    context: str = ""


class ModuleAssistantEngine:
    """Lets Claude answer a question by reading a module's data through its tools."""

    MAXIMUM_TOOL_CALLS: ClassVar[int] = 6
    HISTORY_KEPT: ClassVar[int] = 6
    FACTS_MAXIMUM_LENGTH: ClassVar[int] = 30000
    NEXT_QUESTIONS_KEPT: ClassVar[int] = 3
    NEXT_QUESTION_MAXIMUM_LENGTH: ClassVar[int] = 90
    ANSWER_MAXIMUM_LENGTH: ClassVar[int] = 1500
    CONTEXT_MAXIMUM_LENGTH: ClassVar[int] = 3000
    NOTE_FACTS_LENGTH: ClassVar[int] = 800
    NOTES_KEPT: ClassVar[int] = 3
    MAXIMUM_OUTPUT_TOKENS: ClassVar[int] = 4000
    REQUEST_TIMEOUT_SECONDS: ClassVar[float] = 60.0
    REFUSAL_FALLBACK_BETA: ClassVar[str] = "server-side-fallback-2026-07-01"
    ANSWER_FORMAT: ClassVar[dict[str, object]] = {
        "type": "json_schema",
        "schema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "next_questions": {"type": "array", "items": {"type": "string"}},
                "needs_no_data": {"type": "boolean"},
            },
            "required": ["answer", "next_questions", "needs_no_data"],
            "additionalProperties": False,
        },
    }
    _NUMBER_PATTERN: ClassVar[re.Pattern[str]] = re.compile("\\d(?:[\\d   ]*\\d)?")
    RULES: ClassVar[str] = (
        "Tu es l’assistant intégré à DevLeadHunter, le logiciel de prospection d’un développeur indépendant. "
        "{subject}\n\n"
        "Il te pose ses questions depuis son téléphone ou son ordinateur, comme à un collègue qui a le logiciel "
        "sous les yeux. Tes outils lisent ses données en direct : c’est ta seule source. Tu ne connais aucun de "
        "ses chiffres, de ses clients ni de ses messages par toi-même, donc chaque affirmation sur ses données "
        "doit venir d’un outil appelé pour cette question, même quand la conversation contient déjà une réponse "
        "proche (les données ont pu changer, et la page n’affiche des fiches que si un outil vient de les lire).\n\n"
        "Comment travailler :\n"
        "- Appelle les outils qu’il faut, plusieurs si la question croise ou compare des choses, puis réponds.\n"
        "- Une question de suite (« et à Nantes ? », « les plus chères ? », « parle-moi de la première ») reprend "
        "les filtres et les fiches de l’échange précédent, rappelés sous « Données lues » dans la conversation.\n"
        "- Sous ta réponse, la page affiche d’elle-même les fiches, le graphique ou l’encadré rendus par ton "
        "dernier outil. Ne recopie donc pas la liste : dis ce qu’il faut en retenir, ce qui ressort, ce qui "
        "mérite son attention, et réponds précisément à ce qu’il a demandé.\n"
        "- Écris en français simple, au vouvoiement, en deux ou trois phrases courtes, soixante mots au plus : il "
        "lit sur son téléphone, entre deux tâches. Pas de titre, pas de liste à puces, pas de gras. Donne les "
        "chiffres tels que les outils les donnent.\n"
        "- Les « id » des résultats servent à tes appels d’outils : ne les écris jamais dans ta réponse. Quand ta "
        "réponse porte sur des fiches précises, rappelle l’outil qui les affiche pour qu’il les ait sous les yeux.\n"
        "- Tu lis ses données, tu n’agis pas : tu ne peux ni envoyer ni modifier un message. Pour agir, il ouvre "
        "la fiche que la page affiche ; ne propose donc pas d’envoyer ou d’écrire à sa place.\n"
        "- Si ses données ne permettent pas de répondre, dis-le franchement et propose ce que tu peux regarder à "
        "la place.\n\n"
        "Ta réponse finale est un objet JSON : « answer » (ta réponse), « next_questions » (deux ou trois "
        "questions de suite courtes, formulées comme il les poserait, que tes outils savent traiter) et "
        "« needs_no_data » (true seulement pour un bonjour, une question sur ce que tu sais faire ou une "
        "demande hors sujet, où tu réponds sans lire ses données et sans rien affirmer sur elles)."
    )
    READ_FIRST_REMINDER: ClassVar[str] = (
        "Tu as répondu sans appeler d’outil, donc sans rien lire de ses données. Si la question porte sur elles, "
        "appelle maintenant l’outil qui convient. Si elle n’en a vraiment pas besoin, redonne ta réponse avec "
        "« needs_no_data » à true, sans chiffre ni nom tiré de ses données."
    )

    KNOWN_NUMBERS_REMINDER: ClassVar[str] = (
        "Ta réponse contient au moins un nombre qui ne figure pas dans ce que tes outils ont lu (un calcul, un "
        "arrondi ou une estimation de ta part). Redonne-la en ne gardant que les nombres écrits tels quels dans "
        "les résultats des outils ; pour un total ou un écart, appelle l’outil qui le donne."
    )
    CARDS_KEPT: ClassVar[int] = 12

    def __init__(self) -> None:
        self._client: anthropic.AsyncAnthropic | None = None

    @property
    def is_available(self) -> bool:
        """Whether the core holds a key to hold the conversation with Claude."""
        return bool(settings.anthropic_api_key)

    async def answer(
        self,
        db: Session,
        user_id: int,
        *,
        subject: str,
        tools: Sequence[AssistantTool],
        question: str,
        history: Sequence[AssistantPastExchange],
    ) -> AssistantOutcome | None:
        """
        Answer a question with the module's tools.

        Args:
            db: Active database session; its connection goes back to the pool while the model thinks.
            user_id: The owner whose data the tools read.
            subject: What the module holds, in a few sentences the model reads.
            tools: The tools the model may call.
            question: The owner's words.
            history: The conversation so far, oldest first.

        Returns:
            The answer, None when the model is off, failed, refused or never gave a usable answer: the module then
            answers with its own rules.
        """
        if not self.is_available:
            return None
        tools_by_name: dict[str, AssistantTool] = {tool.name: tool for tool in tools}
        messages: list[dict[str, Any]] = []
        for past in list(history)[-self.HISTORY_KEPT :]:
            messages.append({"role": "user", "content": past.question})
            messages.append({"role": "assistant", "content": self._past_answer(past)})
        messages.append({"role": "user", "content": question})
        results: list[AssistantToolResult] = []
        read_notes: list[str] = []
        was_asked_to_read: bool = False
        was_asked_to_recount: bool = False
        for _round in range(self.MAXIMUM_TOOL_CALLS + 2):
            db.commit()
            response: Any | None = await self._ask_claude(subject, tools, messages)
            if response is None or response.stop_reason not in ("tool_use", "end_turn"):
                break
            if response.stop_reason == "tool_use":
                if len(results) >= self.MAXIMUM_TOOL_CALLS:
                    break
                messages.append({"role": "assistant", "content": response.content})
                tool_results: list[dict[str, object]] = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_results.append(self._tool_result(db, user_id, tools_by_name, block, results, read_notes))
                messages.append({"role": "user", "content": tool_results})
                continue
            written: dict[str, object] | None = self._written_answer(response)
            if written is None:
                break
            answer_text: object = written.get("answer")
            if not isinstance(answer_text, str) or not answer_text.strip():
                break
            if results or (was_asked_to_read and written.get("needs_no_data") is True):
                states_known_numbers: bool = self._states_only_known_numbers(answer_text, results, question, history)
                if results and not states_known_numbers and not was_asked_to_recount:
                    was_asked_to_recount = True
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": self.KNOWN_NUMBERS_REMINDER})
                    continue
                return self._outcome(
                    answer_text.strip(), written.get("next_questions"), results, read_notes, question, history
                )
            if was_asked_to_read:
                break
            was_asked_to_read = True
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": self.READ_FIRST_REMINDER})
        if results:
            return self._outcome(None, None, results, read_notes, question, history)
        return None

    async def _ask_claude(
        self, subject: str, tools: Sequence[AssistantTool], messages: list[dict[str, Any]]
    ) -> Any | None:
        """
        One turn of Claude.

        Args:
            subject: What the module holds.
            tools: The tools it may call.
            messages: The conversation so far, with the tool results.

        Returns:
            Its message, None when the call failed: the reason is logged and the module answers with its own rules.
        """
        try:
            return await self._create_message(
                model=settings.assistant_model,
                max_tokens=self.MAXIMUM_OUTPUT_TOKENS,
                betas=[self.REFUSAL_FALLBACK_BETA],
                fallbacks="default",
                system=[
                    {
                        "type": "text",
                        "text": self.RULES.format(subject=subject),
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=[
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": {
                            "type": "object",
                            "properties": tool.parameters,
                            "additionalProperties": False,
                        },
                    }
                    for tool in tools
                ],
                output_config={"effort": settings.assistant_effort, "format": self.ANSWER_FORMAT},
                messages=messages,
            )
        except anthropic.RateLimitError:
            logger.warning("[ModuleAssistant] Claude rate limit reached")
        except anthropic.APIStatusError as error:
            logger.warning("[ModuleAssistant] Claude answered %s: %s", error.status_code, error.message)
        except anthropic.APIConnectionError:
            logger.warning("[ModuleAssistant] Claude could not be reached", exc_info=True)
        return None

    async def _create_message(self, **request: Any) -> Any:
        """Send one request to the Messages API (the seam the tests replace)."""
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(
                api_key=settings.anthropic_api_key, timeout=self.REQUEST_TIMEOUT_SECONDS
            )
        return await self._client.beta.messages.create(**request)

    def _tool_result(
        self,
        db: Session,
        user_id: int,
        tools_by_name: dict[str, AssistantTool],
        block: Any,
        results: list[AssistantToolResult],
        read_notes: list[str],
    ) -> dict[str, object]:
        """
        Run the tool a ``tool_use`` block asks for.

        Args:
            db: Active database session.
            user_id: The owner whose data the tool reads.
            tools_by_name: The module's tools.
            block: The model's call.
            results: What the tools read so far; a successful call is added to it.
            read_notes: The calls and what they read, as the next question will be reminded of them.

        Returns:
            The ``tool_result`` block that answers the call, an error the model can read when the tool failed.
        """
        tool: AssistantTool | None = tools_by_name.get(str(block.name))
        arguments: AssistantToolArguments = (
            {str(key): value for key, value in block.input.items()} if isinstance(block.input, dict) else {}
        )
        if tool is None:
            return {"type": "tool_result", "tool_use_id": block.id, "content": "Outil inconnu.", "is_error": True}
        try:
            result: AssistantToolResult = tool.run(db, user_id, arguments)
        except Exception:
            db.rollback()
            logger.warning("[ModuleAssistant] tool %s failed with %s", tool.name, arguments, exc_info=True)
            return {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": "La lecture a échoué. Dites que cette information n’est pas disponible pour l’instant.",
                "is_error": True,
            }
        results.append(result)
        facts: str = json.dumps(result.facts, ensure_ascii=False, default=str)
        if len(facts) > self.FACTS_MAXIMUM_LENGTH:
            facts = facts[: self.FACTS_MAXIMUM_LENGTH] + "… (coupé)"
        content: str = f"{facts}\nEn une phrase : {result.sentence}"
        note_facts: str = facts if len(facts) <= self.NOTE_FACTS_LENGTH else facts[: self.NOTE_FACTS_LENGTH] + "…"
        read_notes.append(f"{tool.name}({json.dumps(arguments, ensure_ascii=False)}) → {result.sentence} {note_facts}")
        return {"type": "tool_result", "tool_use_id": block.id, "content": content}

    @staticmethod
    def _written_answer(response: Any) -> dict[str, object] | None:
        """The JSON object of a final message, None when its text is not one."""
        text: str | None = next((block.text for block in response.content if block.type == "text"), None)
        if text is None:
            return None
        try:
            written: object = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(written, dict):
            return None
        return {str(key): value for key, value in written.items()}  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]

    def _past_answer(self, past: AssistantPastExchange) -> str:
        """An earlier answer as the model reads it again, with what its tools had read."""
        if not past.context:
            return past.answer
        return f"{past.answer}\n\nDonnées lues pour cette réponse :\n{past.context[: self.CONTEXT_MAXIMUM_LENGTH]}"

    def _outcome(
        self,
        written: str | None,
        offered_questions: object,
        results: list[AssistantToolResult],
        read_notes: list[str],
        question: str,
        history: Sequence[AssistantPastExchange],
    ) -> AssistantOutcome:
        """
        Put together the model's words and what the tools found.

        Args:
            written: The model's answer, None when it never wrote one.
            offered_questions: The questions it offers to carry on with, as it gave them.
            results: What the tools read, in order.
            read_notes: Each tool call with what it read.
            question: The owner's words.
            history: The conversation so far.

        Returns:
            The answer; the tools' own sentences replace words that state a number no tool gave.
        """
        tool_sentences: str = " ".join(result.sentence for result in results)
        text: str = written[: self.ANSWER_MAXIMUM_LENGTH] if written else tool_sentences
        if written and not self._states_only_known_numbers(written, results, question, history):
            logger.info("[ModuleAssistant] answer set aside, it states a number no tool gave: %s", written)
            text = tool_sentences or "Je n’ai pas trouvé cette information dans vos données."
        next_questions: list[str] = []
        if isinstance(offered_questions, list):
            next_questions = [
                offered.strip()
                for offered in offered_questions  # pyright: ignore[reportUnknownVariableType]
                if isinstance(offered, str) and 0 < len(offered.strip()) <= self.NEXT_QUESTION_MAXIMUM_LENGTH
            ][: self.NEXT_QUESTIONS_KEPT]
        return AssistantOutcome(
            text=text,
            cards=self._cards_to_draw(results),
            chart=next((result.chart for result in reversed(results) if result.chart is not None), None),
            highlight=next((result.highlight for result in reversed(results) if result.highlight is not None), None),
            next_questions=next_questions,
            context="\n".join(read_notes[-self.NOTES_KEPT :])[: self.CONTEXT_MAXIMUM_LENGTH],
        )

    @classmethod
    def _cards_to_draw(cls, results: list[AssistantToolResult]) -> list[object]:
        """
        The cards the page draws under an answer.

        Returns:
            Those of the last call that found some, joined by the earlier calls of the same turn that hold cards of
            the same kind (two searches for two words), each card once, twelve at most.
        """
        with_cards: list[AssistantToolResult] = [result for result in results if result.cards]
        if not with_cards:
            return []
        if with_cards[-1].is_selection:
            return list(with_cards[-1].cards)[: cls.CARDS_KEPT]
        kind: type = type(with_cards[-1].cards[0])
        drawn: list[object] = []
        for result in with_cards:
            for card in result.cards:
                if isinstance(card, kind) and card not in drawn:
                    drawn.append(card)
        return drawn[-cls.CARDS_KEPT :] if len(with_cards) == 1 else drawn[: cls.CARDS_KEPT]

    @classmethod
    def _states_only_known_numbers(
        cls,
        written: str,
        results: list[AssistantToolResult],
        question: str,
        history: Sequence[AssistantPastExchange],
    ) -> bool:
        """Whether every number of an answer was given by a tool, or said earlier in the conversation."""
        known_text: str = " ".join(
            [
                question,
                *(f"{past.question} {past.answer} {past.context}" for past in history),
                *(
                    json.dumps(result.facts, ensure_ascii=False, default=str) + " " + result.sentence
                    for result in results
                ),
            ]
        )
        known: set[str] = cls._numbers_of(known_text, with_each_group=True)
        return cls._numbers_of(written, with_each_group=False) <= known

    @classmethod
    def _numbers_of(cls, text: str, *, with_each_group: bool) -> set[str]:
        """
        The numbers a text states, written without their thousands spaces (« 2 000 » and « 2000 » are one).

        Args:
            text: The text to read.
            with_each_group: Whether the groups of digits a space separates also count alone (« 12 000 » then also
                gives « 12 »), so two numbers that follow each other in the facts are both known.

        Returns:
            The numbers, as digits.
        """
        numbers: set[str] = set()
        for match in cls._NUMBER_PATTERN.finditer(text):
            numbers.add(re.sub(r"\D", "", match.group(0)))
            if with_each_group:
                numbers.update(group for group in re.split(r"\D+", match.group(0)) if group)
        return numbers


module_assistant_engine: ModuleAssistantEngine = ModuleAssistantEngine()
