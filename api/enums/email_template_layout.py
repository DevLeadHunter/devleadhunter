"""
Enum for the dressing a prospecting email leaves in.

Stored as a plain string in a ``String`` column, like the template category. The dressing is a
choice of the template so the campaign A/B test can compare the same text, dressed or not.
"""

from enum import Enum


class EmailTemplateLayout(str, Enum):
    """How the rendered body of a template is presented to the prospect."""

    PLAIN = "plain"
    CARD = "card"
    CARD_TABLE = "card_table"
