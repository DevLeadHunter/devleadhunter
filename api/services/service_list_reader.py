"""Read the services a business lists in its own words: a Facebook intro, a page description, a register purpose."""

from __future__ import annotations

import re

from services.decision_maker.normalize import fold

MAX_SERVICES = 12
MIN_LIST_ITEMS = 3
MAX_ITEM_WORDS = 7
MAX_ITEM_CHARS = 60
MIN_ITEM_CHARS = 3
MIN_SERVICE_SHARE = 0.6

_EMOJI_RE = re.compile("[←-⯿☀-➿\U0001f000-\U0001faff]️?")
_BULLET_RE = re.compile(r"\s*(?:\n|•|·|\||;|\s[-–]\s)\s*")
_SENTENCE_END_RE = re.compile(r"(?<=[a-zà-ÿ0-9)])\s*[.!?]+\s+(?=[A-ZÀ-Ý«\"])|\s+\.\s+")
_TRAILING_NOISE_RE = re.compile(r"(?:\s*(?:\.{2,}|…|\betc\b\.?|!|\.)\s*)+$", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?:\d[\s().-]*){6,}")
_PROSE_WORD_RE = re.compile(
    r"\b(?:nous|vous|je|est|sont|propose|proposons|offre|offrons|situ[ée]e?s?|bas[ée]e?s?|"
    r"depuis|plus de|ans d|faites|contactez|appelez|n'h[ée]sitez)\b",
    re.IGNORECASE,
)
_COMPANY_PREFIX_RE = re.compile(r"^(?:l'|une? )?(?:entreprise|soci[ée]t[ée])\s+(?:de\s+|d')", re.IGNORECASE)
_NOT_A_SERVICE_RE = re.compile(
    r"\b(?:facebook|instagram|tiktok|youtube|linkedin|soumissions?|devis|gratuite?s?|estimations?|garanties?|"
    r"contact|t[ée]l[ée]phone|r[ée]servations?|rendez-vous|horaires?|ouvert|bienvenue|merci|sans engagement|"
    r"engagement|qualit[ée]|professionnalisme|satisfaction|prix|tarifs?)\b",
    re.IGNORECASE,
)
_BUSINESS_NOUN_RE = re.compile(
    r"^(?:l'|la |le |les |une? )?(?:entreprise|soci[ée]t[ée]|garage|atelier|[ée]tablissement)s?\b", re.IGNORECASE
)


class ServiceListReader:
    """Pick the service names out of a text the business wrote, and only when the text really lists them."""

    @classmethod
    def services_in(cls, text: str | None, *, business_name: str | None = None, city: str | None = None) -> list[str]:
        """
        The services a text lists, in its order, or nothing when the text is prose rather than a list.

        A list is a run of at least three short items, whether bulleted (« Achat • Vente • Reprise ») or
        written as one comma sentence (« Dallage, pavage, taille des arbres… »); lines that sell rather than
        name a service (quote, phone, network, guarantee) and the business's own name are left out.

        Args:
            text: The business's text.
            business_name: The prospect's name, never a service.
            city: The prospect's town: a list naming it is a list of places, not of services.

        Returns:
            The service names, cleaned and capitalized, at most ``MAX_SERVICES``.
        """
        if not text or not text.strip():
            return []
        bulleted_lines = [line for line in _BULLET_RE.split(_EMOJI_RE.sub("\n", text)) if line.strip()]
        services: list[str] = []
        if len(bulleted_lines) >= MIN_LIST_ITEMS:
            services += cls._accepted_items(bulleted_lines, business_name=business_name, city=city)
        for line in bulleted_lines:
            for sentence in _SENTENCE_END_RE.split(line):
                items = [item for item in sentence.split(",") if item.strip()]
                if len(items) >= MIN_LIST_ITEMS:
                    services += cls._accepted_items(items, business_name=business_name, city=city)
        return cls._unique(services)[:MAX_SERVICES]

    @classmethod
    def _accepted_items(cls, items: list[str], *, business_name: str | None, city: str | None) -> list[str]:
        """The service names of one candidate list, or none when too few of its items read as services."""
        cleaned = [cls._clean(item) for item in items]
        if city and any(fold(item) == fold(city) for item in cleaned):
            return []
        services = [item for item in cleaned if cls._is_service(item, business_name=business_name)]
        if len(services) < MIN_LIST_ITEMS or len(services) < MIN_SERVICE_SHARE * len(items):
            return []
        return services

    @staticmethod
    def _clean(item: str) -> str:
        """One item trimmed of bullets, trailing dots and « etc. », spaced and capitalized."""
        text = " ".join(item.split()).strip(" -–:.")
        text = _TRAILING_NOISE_RE.sub("", text).strip(" -–:,")
        text = re.sub(r"\s*/\s*", "/", text)
        text = re.sub(r"^et\s+", "", text, flags=re.IGNORECASE)
        text = _COMPANY_PREFIX_RE.sub("", text)
        if text.isupper():
            text = text.lower()
        return text[:1].upper() + text[1:]

    @staticmethod
    def _is_service(item: str, *, business_name: str | None) -> bool:
        """Whether a cleaned item names a service rather than selling, situating or naming the business."""
        if not MIN_ITEM_CHARS <= len(item) <= MAX_ITEM_CHARS or len(item.split()) > MAX_ITEM_WORDS:
            return False
        if "@" in item or "http" in item.lower() or "www." in item.lower() or _PHONE_RE.search(item):
            return False
        if _PROSE_WORD_RE.search(item) or _NOT_A_SERVICE_RE.search(item) or _BUSINESS_NOUN_RE.search(item):
            return False
        return not (business_name and fold(business_name) and fold(business_name) in fold(item))

    @staticmethod
    def _unique(services: list[str]) -> list[str]:
        """The services without repeats, first spelling kept."""
        seen: set[str] = set()
        unique: list[str] = []
        for service in services:
            key = fold(service)
            if key not in seen:
                seen.add(key)
                unique.append(service)
        return unique
