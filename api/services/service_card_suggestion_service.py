"""
AI-composed section cards (« Nos spécialités ») for a demo site.

Reproduces what the operator used to do by hand with an assistant and Storyblok: look at every
prospect photo, read the photographed menus and the reviews, then pick the best dish photo for
each card and write a short title + description. Inputs are the photo labels produced by
:mod:`services.photo_labeling_service`, the enrichment (description, reviews, service chips) and
the section constraints declared by the template (``TEMPLATE_META["service_cards"]``).

The output is validated hard: a card can only carry a photo of the site's pool that the vision
pass called a dish or a drink, a photo is used at most once, lengths are capped, and the count is
bounded by the template's ``min_cards`` / ``max_cards``.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from core.config import settings
from services.llm_service import llm_service
from services.photo_labels import PHOTO_KIND_MENU_BOARD, is_card_worthy

logger = logging.getLogger(__name__)


class ServiceCardsUnavailableError(RuntimeError):
    """The AI suggestion cannot run (no Groq key on the server)."""


MAX_TITLE_CHARS = 60
MAX_DESCRIPTION_CHARS = 160
MAX_REASON_CHARS = 200
DEFAULT_MIN_CARDS = 4
DEFAULT_MAX_CARDS = 6
_MAX_REVIEWS_IN_PROMPT = 12
_MAX_REVIEW_CHARS = 300
_MAX_DESCRIPTION_IN_PROMPT = 1200
_WHITESPACE_RE = re.compile(r"\s+")

# Human labels of the photo kinds, for the inventory handed to the writing model.
_KIND_LABELS_FR: dict[str, str] = {
    "dish": "plat",
    "drink": "boisson",
    "truck": "camion / façade",
    "menu_board": "menu affiché",
    "interior": "intérieur",
    "people": "personnes",
    "event": "événement",
    "logo_or_flyer": "logo / flyer",
    "other": "autre",
}


@dataclass
class ServiceCardsConfig:
    """Section constraints declared by a template (see ``TEMPLATE_META["service_cards"]``)."""

    enabled: bool = False
    heading: str = "Prestations"
    subject: str = "prestations"
    min_cards: int = DEFAULT_MIN_CARDS
    max_cards: int = DEFAULT_MAX_CARDS
    with_images: bool = True

    @classmethod
    def from_meta(cls, raw: Any) -> ServiceCardsConfig:
        """Build a config from a template's raw meta entry; a missing or invalid entry means disabled."""
        if not isinstance(raw, dict):
            return cls()
        min_cards = _as_int(raw.get("min_cards"), DEFAULT_MIN_CARDS)
        max_cards = max(min_cards, _as_int(raw.get("max_cards"), DEFAULT_MAX_CARDS))
        return cls(
            enabled=bool(raw.get("enabled", False)),
            heading=str(raw.get("heading") or "Prestations"),
            subject=str(raw.get("subject") or "prestations"),
            min_cards=max(1, min_cards),
            max_cards=max_cards,
            with_images=bool(raw.get("with_images", True)),
        )

    def as_dict(self) -> dict[str, Any]:
        """Plain dict for API responses."""
        return {
            "enabled": self.enabled,
            "heading": self.heading,
            "subject": self.subject,
            "min_cards": self.min_cards,
            "max_cards": self.max_cards,
            "with_images": self.with_images,
        }


@dataclass
class ServiceCardSuggestionResult:
    """Validated cards plus a summary of what the analysis had to work with."""

    cards: list[dict[str, Any]] = field(default_factory=list)
    analysis: dict[str, Any] = field(default_factory=dict)


def _as_int(value: Any, default: int) -> int:
    """Coerce to int, falling back to ``default``."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_text(value: Any, limit: int) -> str:
    """Trim, collapse whitespace, strip wrapping quotes and cap the length of a model string."""
    text = _WHITESPACE_RE.sub(" ", str(value or "")).strip().strip("\"'«» ")
    return text[:limit].strip()


def photo_inventory_lines(pool: list[str], labels: dict[str, dict[str, Any]]) -> list[str]:
    """One human-readable line per pool photo (1-based index) for the writing prompt."""
    lines: list[str] = []
    for position, url in enumerate(pool, start=1):
        label = labels.get(url)
        if label is None:
            lines.append(f"#{position} · non analysée")
            continue
        kind = _KIND_LABELS_FR.get(str(label.get("kind", "")), "autre")
        parts = [f"#{position} · {kind}"]
        description = str(label.get("description", "")).strip()
        if description:
            parts.append(description)
        dishes = [str(item) for item in label.get("dishes", []) if str(item).strip()]
        if dishes:
            parts.append("plats : " + ", ".join(dishes))
        if is_card_worthy(label):
            parts.append(f"attrait {int(label.get('appeal', 0))}/5")
        lines.append(" · ".join(parts))
    return lines


def eligible_photo_indexes(pool: list[str], labels: dict[str, dict[str, Any]]) -> list[int]:
    """1-based indexes of the card-worthy photos, best appeal first (stable on the pool order)."""
    candidates = [
        (position, labels[url]) for position, url in enumerate(pool, start=1) if is_card_worthy(labels.get(url))
    ]
    candidates.sort(key=lambda item: -int(item[1].get("appeal", 0)))
    return [position for position, _label in candidates]


def menu_dishes(labels: dict[str, dict[str, Any]]) -> list[str]:
    """Every dish read on a photographed menu board, deduplicated, in label order."""
    dishes: list[str] = []
    for label in labels.values():
        if str(label.get("kind", "")) != PHOTO_KIND_MENU_BOARD:
            continue
        for item in label.get("dishes", []):
            text = str(item).strip()
            if text and text.lower() not in {existing.lower() for existing in dishes}:
                dishes.append(text)
    return dishes


def review_excerpts(enrichment: dict[str, Any] | None) -> list[str]:
    """Review texts worth reading for dish names (longest first, capped)."""
    reviews = (enrichment or {}).get("reviews")
    if not isinstance(reviews, list):
        return []
    texts: list[str] = []
    for review in reviews:
        if not isinstance(review, dict):
            continue
        text = _WHITESPACE_RE.sub(" ", str(review.get("text", "") or "")).strip()
        if len(text) >= 12:
            texts.append(text[:_MAX_REVIEW_CHARS])
    texts.sort(key=len, reverse=True)
    return texts[:_MAX_REVIEWS_IN_PROMPT]


class ServiceCardSuggestionService:
    """Writes the section cards from labelled photos, menus and reviews (Groq text model)."""

    @property
    def is_available(self) -> bool:
        """True when a Groq API key is configured."""
        return llm_service.is_configured

    async def suggest(
        self,
        *,
        business_name: str,
        city: str | None,
        category: str | None,
        enrichment: dict[str, Any] | None,
        pool: list[str],
        labels: dict[str, dict[str, Any]],
        config: ServiceCardsConfig,
    ) -> ServiceCardSuggestionResult:
        """Compose the cards for a site.

        Args:
            business_name: The prospect's business name.
            city: Its city, when known.
            category: Its trade / Google category, when known.
            enrichment: The prospect enrichment dict (description, reviews, services…).
            pool: The site's photo pool, in site order (1-based indexes in the prompt).
            labels: Vision labels keyed by pool URL (missing entries = not analysed).
            config: The section constraints of the template.

        Returns:
            Validated cards (possibly fewer than ``min_cards`` when the evidence is thin) and the
            analysis summary; empty cards when the model gave nothing usable.
        """
        eligible = eligible_photo_indexes(pool, labels)
        dishes_read = menu_dishes(labels)
        reviews = review_excerpts(enrichment)
        analysis: dict[str, Any] = {
            "photos_total": len(pool),
            "photos_labelled": sum(1 for url in pool if url in labels),
            "dish_photos": len(eligible),
            "menu_boards": sum(1 for url in pool if str(labels.get(url, {}).get("kind", "")) == PHOTO_KIND_MENU_BOARD),
            "menu_dishes": len(dishes_read),
            "reviews_used": len(reviews),
            "model": settings.groq_model,
        }
        if not self.is_available:
            return ServiceCardSuggestionResult(cards=[], analysis=analysis)

        prompt = self._build_prompt(
            business_name=business_name,
            city=city,
            category=category,
            enrichment=enrichment or {},
            pool=pool,
            labels=labels,
            eligible=eligible,
            dishes_read=dishes_read,
            reviews=reviews,
            config=config,
        )
        answer = await llm_service.complete_json(
            [
                {"role": "system", "content": self._system_prompt(config)},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1600,
            temperature=0.4,
            timeout=75.0,
        )
        cards = self.clean_cards(answer.get("cards") if isinstance(answer, dict) else None, pool, labels, config)
        return ServiceCardSuggestionResult(cards=cards, analysis=analysis)

    @staticmethod
    def _system_prompt(config: ServiceCardsConfig) -> str:
        """Role and hard rules for the writing model."""
        return (
            "Tu es le rédacteur d'un site vitrine pour un commerce de restauration français (food truck, "
            f"restaurant, traiteur). Tu composes la section « {config.heading} » : des cartes qui présentent "
            f"les vrais {config.subject} du commerce, chacune avec la meilleure photo, un titre court et une "
            "description courte et appétissante.\n"
            "Règles absolues :\n"
            "- Tu ne présentes QUE des plats, formules ou boissons attestés par les indices fournis : photos "
            "de plats, menus lus, avis clients, description, liste de services. Jamais un plat inventé, jamais "
            "un ingrédient qui n'est ni visible ni écrit.\n"
            "- Reprends le nom exact du plat quand le menu ou les avis le donnent (ex. « Le Super Marioo »).\n"
            "- Une photo ne peut être choisie que parmi les photos ÉLIGIBLES (plats / boissons), une seule "
            "fois, et doit montrer le plat de la carte. Jamais le camion, un menu, un flyer ou un logo.\n"
            "- Aucun prix dans les titres ni les descriptions.\n"
            f"- Titre : 40 caractères max. Description : 120 caractères max, une phrase, concrète (les "
            "ingrédients vus ou lus), ton chaleureux, sans superlatif creux ni point d'exclamation.\n"
            f"- Entre {config.min_cards} et {config.max_cards} cartes ; vise {config.min_cards} sauf si le "
            "commerce a clairement plus de plats distincts et bien photographiés.\n"
            '- S\'il y a moins de photos éligibles que de cartes, les cartes restantes ont "photo": null.\n'
            "Réponds UNIQUEMENT par un objet JSON : "
            '{"cards": [{"photo": 9, "title": "Le Super Marioo", "description": "Triple steak, bacon fumé, '
            'cheddar et crème de tomate, notre burger XXL maison.", "reason": "Burger star des avis, photo la '
            "plus vendeuse.\"}]}. « reason » (160 caractères max) explique en français, pour l'opérateur, "
            "pourquoi ce plat et cette photo (source : avis, menu, photo)."
        )

    @staticmethod
    def _build_prompt(
        *,
        business_name: str,
        city: str | None,
        category: str | None,
        enrichment: dict[str, Any],
        pool: list[str],
        labels: dict[str, dict[str, Any]],
        eligible: list[int],
        dishes_read: list[str],
        reviews: list[str],
        config: ServiceCardsConfig,
    ) -> str:
        """The evidence handed to the model: business context, photo inventory, menus, reviews."""
        lines: list[str] = [f"Commerce : {business_name}"]
        if city:
            lines.append(f"Ville : {city}")
        if category:
            lines.append(f"Catégorie : {category}")
        description = _WHITESPACE_RE.sub(" ", str(enrichment.get("description", "") or "")).strip()
        if description:
            lines.append(f"Description : {description[:_MAX_DESCRIPTION_IN_PROMPT]}")
        services = [str(item).strip() for item in enrichment.get("services", []) or [] if str(item).strip()]
        if services:
            lines.append("Services / plats déclarés : " + ", ".join(services[:30]))
        lines.append("")
        lines.append(f"Photos disponibles ({len(pool)}), numérotées :")
        lines.extend(photo_inventory_lines(pool, labels))
        lines.append("")
        if eligible:
            lines.append(
                "Photos ÉLIGIBLES pour une carte (meilleur attrait en premier) : "
                + ", ".join(f"#{i}" for i in eligible)
            )
        else:
            lines.append('Aucune photo éligible : toutes les cartes auront "photo": null.')
        if dishes_read:
            lines.append("")
            lines.append("Plats lus sur les menus photographiés : " + " | ".join(dishes_read))
        if reviews:
            lines.append("")
            lines.append("Avis clients :")
            lines.extend(f"- {text}" for text in reviews)
        lines.append("")
        lines.append(
            f"Compose entre {config.min_cards} et {config.max_cards} cartes « {config.heading} » en respectant les règles."
        )
        return "\n".join(lines)

    @staticmethod
    def clean_cards(
        raw_cards: Any,
        pool: list[str],
        labels: dict[str, dict[str, Any]],
        config: ServiceCardsConfig,
    ) -> list[dict[str, Any]]:
        """Validate the model's cards against the pool and the section constraints.

        A photo index outside the pool or pointing at a non-eligible photo is dropped (the card keeps
        its text); a photo used twice keeps its first card; duplicate titles are merged; the count is
        capped at ``max_cards``. Cards left without a photo then receive the best unused eligible
        photo, so a real dish photo is never wasted while a card shows a gallery fallback.
        """
        if not isinstance(raw_cards, list):
            return []
        used_urls: set[str] = set()
        seen_titles: set[str] = set()
        cards: list[dict[str, Any]] = []
        for entry in raw_cards:
            if not isinstance(entry, dict):
                continue
            title = _clean_text(entry.get("title"), MAX_TITLE_CHARS)
            if not title or title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())
            image = ""
            photo_index = _as_int(entry.get("photo"), 0)
            if config.with_images and 1 <= photo_index <= len(pool):
                url = pool[photo_index - 1]
                if is_card_worthy(labels.get(url)) and url not in used_urls:
                    image = url
                    used_urls.add(url)
            cards.append(
                {
                    "title": title,
                    "description": _clean_text(entry.get("description"), MAX_DESCRIPTION_CHARS),
                    "image": image,
                    "reason": _clean_text(entry.get("reason"), MAX_REASON_CHARS),
                    "photo_index": pool.index(image) + 1 if image else None,
                }
            )
            if len(cards) >= config.max_cards:
                break
        if config.with_images:
            spare = [pool[i - 1] for i in eligible_photo_indexes(pool, labels) if pool[i - 1] not in used_urls]
            for card in cards:
                if card["image"] or not spare:
                    continue
                url = spare.pop(0)
                card["image"] = url
                card["photo_index"] = pool.index(url) + 1
        return cards


service_card_suggestion_service = ServiceCardSuggestionService()
