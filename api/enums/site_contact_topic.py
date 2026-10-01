"""
What a visitor writes about on the contact page of the marketing site.
"""

from enum import Enum


class SiteContactTopic(str, Enum):
    """
    Topic picked on the contact form of devleadhunter.fr.

    Attributes:
        DISCOVER: A question before signing up.
        CREDITS: Credits, a purchase or an invoice.
        ACCOUNT: Help with an existing account.
        PRIVACY: A personal data request (access, correction, deletion).
        OTHER: Anything else.
    """

    DISCOVER = "discover"
    CREDITS = "credits"
    ACCOUNT = "account"
    PRIVACY = "privacy"
    OTHER = "other"

    @property
    def label(self) -> str:
        """French label shown in the email and the notification sent to the publisher."""
        return _TOPIC_LABELS[self]


_TOPIC_LABELS: dict[SiteContactTopic, str] = {
    SiteContactTopic.DISCOVER: "Découvrir l'outil",
    SiteContactTopic.CREDITS: "Crédits et facturation",
    SiteContactTopic.ACCOUNT: "Aide sur mon compte",
    SiteContactTopic.PRIVACY: "Données personnelles",
    SiteContactTopic.OTHER: "Autre",
}
