"""Languages the assistant widget speaks up front."""

from enum import Enum


class AssistantWidgetLanguage(str, Enum):
    """A language the widget offers greetings and suggestions in (the model still replies in any language)."""

    FR = "fr"
    NL = "nl"
    EN = "en"
    DE = "de"
    LU = "lu"
