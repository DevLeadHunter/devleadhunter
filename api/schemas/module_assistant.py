"""The assistant of a product module: the question the owner asks and the parts of an answer every module shares."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AssistantSuggestionTone = Literal["blue", "violet", "green", "amber", "red"]


class AssistantSuggestion(BaseModel):
    """
    A question the owner sends with one touch.

    Attributes:
        label: The question, as it is sent.
        tone: The colour of its icon tile.
        icon: Its icon (an ``i-lucide-…`` name).
    """

    label: str
    tone: AssistantSuggestionTone
    icon: str


class AssistantHome(BaseModel):
    """
    What the assistant shows before the first question.

    Attributes:
        lead: The sentence under the title.
        suggestions: The questions offered.
    """

    lead: str
    suggestions: list[AssistantSuggestion]


class AssistantPastExchange(BaseModel):
    """
    A question already asked in the conversation, with the answer it got.

    Attributes:
        question: The owner's words.
        answer: The answer in words, as the page showed it.
        context: What the tools read to write it, as the answer handed it to the page.
    """

    question: str = Field(min_length=1, max_length=500)
    answer: str = Field(max_length=2000)
    context: str = Field(default="", max_length=4000)


class AssistantQuestion(BaseModel):
    """
    A question asked to the assistant.

    Attributes:
        question: The owner's words.
        history: The conversation so far, oldest first, so a follow-up question keeps its thread.
    """

    question: str = Field(min_length=1, max_length=500)
    history: list[AssistantPastExchange] = Field(default_factory=list[AssistantPastExchange], max_length=12)


class AssistantBar(BaseModel):
    """
    One bar of a chart.

    Attributes:
        label: What is counted.
        value: How many.
    """

    label: str
    value: int


class AssistantChart(BaseModel):
    """
    A chart of counts, largest first.

    Attributes:
        title: Its title.
        bars: Its bars.
    """

    title: str
    bars: list[AssistantBar]


class AssistantHighlight(BaseModel):
    """
    One thing to look at first, such as a reply received.

    Attributes:
        title: Who or what it is about.
        badge: Its state in a word.
        meta: The line under the title.
        text: What was said, None when there is nothing to quote.
        link_label: The label of its link.
        link_to: The page the link opens.
    """

    title: str
    badge: str
    meta: str
    text: str | None
    link_label: str
    link_to: str


class AssistantAnswer(BaseModel):
    """
    The parts of an answer every module shares; a module adds its own cards.

    Attributes:
        text: The answer in a sentence or two, every figure read from the database.
        chart: A chart, None when the answer has none.
        highlight: One thing to look at first, None when there is none.
        next_questions: Questions to carry on with.
        context: What the tools read, in short; the page sends it back with the next question and never shows it.
    """

    text: str
    chart: AssistantChart | None = None
    highlight: AssistantHighlight | None = None
    next_questions: list[str] = Field(default_factory=list[str])
    context: str = ""
