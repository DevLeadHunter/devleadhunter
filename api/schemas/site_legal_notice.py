"""Pydantic schemas of the legal block served with a generated site (legal notice and privacy policy)."""

from typing import Literal

from pydantic import BaseModel

SiteLegalBlockKind = Literal["identity", "text"]


class SiteLegalLine(BaseModel):
    """One line of a block: a labelled value or a sentence, linked when it can be tapped (email, phone, site)."""

    label: str | None = None
    text: str
    href: str | None = None


class SiteLegalBlock(BaseModel):
    """A titled group of lines: an identity (name, address, contacts, one per line) or paragraphs of text."""

    heading: str
    kind: SiteLegalBlockKind = "text"
    lines: list[SiteLegalLine]


class SiteLegalSection(BaseModel):
    """A part of the legal page, reached by its anchor from the footer link."""

    anchor: str
    title: str
    blocks: list[SiteLegalBlock]


class SiteLegalLink(BaseModel):
    """A footer link to one section of the legal page."""

    label: str
    anchor: str


class SiteLegalNotice(BaseModel):
    """The legal block of a served site, computed when it is served and never stored in its content."""

    locale: str
    page_title: str
    accent_color: str | None = None
    demo_notice: str | None = None
    links: list[SiteLegalLink]
    sections: list[SiteLegalSection]
