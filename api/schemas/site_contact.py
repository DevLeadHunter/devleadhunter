"""
Payload of the contact form of the marketing site (devleadhunter.fr/contact).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from enums.site_contact_topic import SiteContactTopic


class SiteContactRequest(BaseModel):
    """
    A visitor's message.

    ``website`` is a honeypot: the field is hidden from people, so only a bot fills it.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    topic: SiteContactTopic = SiteContactTopic.DISCOVER
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    message: str = Field(min_length=1, max_length=5000)
    locale: str | None = Field(default=None, max_length=8)
    website: str | None = Field(default=None, max_length=300)

    @field_validator("name", "phone")
    @classmethod
    def _collapse_to_single_line(cls, value: str | None) -> str | None:
        """Collapse line breaks and repeated spaces: the name lands in an email subject and a notification title."""
        if value is None:
            return None
        return " ".join(value.split()) or None


class SiteContactResponse(BaseModel):
    """Answer once the message is on its way."""

    status: Literal["sent"] = "sent"
