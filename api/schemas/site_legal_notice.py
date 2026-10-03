"""Pydantic schemas of the legal block served with a generated site (legal notice and privacy policy)."""

from typing import Literal

from pydantic import BaseModel

SiteLegalBlockKind = Literal["identity", "text"]
SiteLegalPageKind = Literal["legal", "privacy"]


class SiteLegalLine(BaseModel):
    """One line of a block: a labelled value or a sentence, linked when it can be tapped (email, phone, site).

    In an identity, ``paragraph`` groups the lines shown together: the name and the address, then the
    contacts, then the identifiers.
    """

    label: str | None = None
    text: str
    href: str | None = None
    paragraph: int = 0


class SiteLegalBlock(BaseModel):
    """A titled group of lines: an identity (name, address, contacts, one per line) or paragraphs of text."""

    heading: str
    kind: SiteLegalBlockKind = "text"
    intro: str | None = None
    lines: list[SiteLegalLine]


class SiteLegalSection(BaseModel):
    """One legal page of the site: the legal notice or the privacy policy, with the sentence under its title."""

    page: SiteLegalPageKind
    anchor: str
    title: str
    intro: str
    blocks: list[SiteLegalBlock]


class SiteLegalLink(BaseModel):
    """A footer link to one legal page of the site."""

    label: str
    page: SiteLegalPageKind
    anchor: str


class SiteLegalNotice(BaseModel):
    """The legal block of a served site, computed when it is served and never stored in its content."""

    locale: str
    page_title: str
    accent_color: str | None = None
    demo_notice: str | None = None
    links: list[SiteLegalLink]
    sections: list[SiteLegalSection]
