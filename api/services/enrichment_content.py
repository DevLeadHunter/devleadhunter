"""
Pure mapping of enrichment data into a template's content_json.

Kept dependency-free (no scrapers, no DB) so it can be imported by
``storyblok_service`` without pulling the heavy scraper import chain.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

MAX_GALLERY_PHOTOS = 8
MAX_REVIEWS = 6
DEFAULT_REVIEW_RATING = 5
GOOGLE_RATING_LABEL = "Avis Google"


@dataclass(frozen=True)
class TemplateBlokNames:
    """
    Blok component names of one template family.

    Templates migrated to Nuxt layers namespace their bloks (``lumen_hero``, ``cuivre_hero``…),
    so the same mapping runs three times over three sets of names.
    """

    hero: str
    trust: str
    gallery: str
    gallery_item: str
    reviews: str
    review_item: str
    contact: str
    uid_prefix: str
    about: str | None = None
    carries_location: bool = False
    rates_first_trust_item: bool = False


BLOK_FAMILIES: tuple[TemplateBlokNames, ...] = (
    TemplateBlokNames(
        hero="hero",
        trust="trust",
        gallery="gallery",
        gallery_item="gallery_item",
        reviews="testimonials",
        review_item="testimonial_item",
        contact="contact",
        uid_prefix="",
        carries_location=True,
        rates_first_trust_item=True,
    ),
    TemplateBlokNames(
        hero="lumen_hero",
        trust="lumen_trust",
        gallery="lumen_gallery",
        gallery_item="lumen_gallery_item",
        reviews="lumen_reviews",
        review_item="lumen_review_item",
        contact="lumen_contact",
        uid_prefix="lumen-",
    ),
    TemplateBlokNames(
        hero="cuivre_hero",
        trust="cuivre_trust",
        gallery="cuivre_gallery",
        gallery_item="cuivre_gallery_item",
        reviews="cuivre_reviews",
        review_item="cuivre_review_item",
        contact="cuivre_contact",
        uid_prefix="cuivre-",
        about="cuivre_about",
    ),
)


class EnrichmentContentMapper:
    """
    Merges scraped enrichment data (photos, reviews, rating, opening hours) into a content_json.

    Template-agnostic: only bloks the content already declares are filled, so a template that has
    no gallery simply keeps its own copy.
    """

    @staticmethod
    def format_rating(rating: float | None) -> str | None:
        """
        Format a numeric rating the French way.

        Args:
            rating: Raw Google rating.

        Returns:
            The rating as "4,9/5", or None when it is missing or unparseable.
        """
        if rating is None:
            return None
        try:
            return f"{float(rating):.1f}".replace(".", ",") + "/5"
        except (TypeError, ValueError):
            return None

    @staticmethod
    def format_hours(hours: list | None) -> str | None:
        """
        Flatten structured opening hours into the one-line string the contact blok displays.

        Args:
            hours: Rows of ``{"day": …, "hours": …}``.

        Returns:
            The joined string, or None when no row is usable.
        """
        if not hours:
            return None
        parts: list[str] = [
            f"{row['day']} {row['hours']}"
            for row in hours
            if isinstance(row, dict) and row.get("day") and row.get("hours")
        ]
        return " · ".join(parts) if parts else None

    @classmethod
    def apply_to_content(cls, content_json: dict[str, Any], enrichment: dict[str, Any] | None) -> dict[str, Any]:
        """
        Merge enrichment data into a template's content_json.

        Photos feed the hero image and the gallery, reviews feed the testimonials, the rating feeds
        the trust block, and the opening hours feed the contact block.

        Args:
            content_json: Template content, left untouched.
            enrichment: Scraped data, or None when the prospect has none.

        Returns:
            A deep copy carrying the enrichment, or the input unchanged when nothing applies.
        """
        if not enrichment or not isinstance(content_json, dict):
            return content_json

        content: dict[str, Any] = copy.deepcopy(content_json)
        body = content.get("body")
        if not isinstance(body, list):
            return content

        photos: list[str] = [p for p in enrichment.get("photos", []) if isinstance(p, str)]
        reviews: list[dict] = [r for r in enrichment.get("reviews", []) if isinstance(r, dict)]
        rating_label: str | None = cls.format_rating(enrichment.get("rating"))
        hours_label: str | None = cls.format_hours(enrichment.get("opening_hours"))

        for blok in body:
            if not isinstance(blok, dict):
                continue
            component = blok.get("component")
            family: TemplateBlokNames | None = next(
                (f for f in BLOK_FAMILIES if component in cls._known_components(f)), None
            )
            if family is None:
                continue

            if component == family.hero and photos:
                blok["image"] = photos[0]

            elif component == family.about and len(photos) > 1:
                blok["image"] = photos[1]

            elif component == family.trust and rating_label:
                cls._apply_rating(blok, rating_label, family)

            elif component == family.gallery and photos:
                blok["items"] = cls._build_gallery_items(photos, family)

            elif component == family.reviews and reviews:
                mapped: list[dict[str, Any]] = cls._build_review_items(reviews, family)
                if mapped:
                    blok["items"] = mapped

            elif component == family.contact and hours_label:
                blok["hours"] = hours_label

        return content

    @staticmethod
    def _known_components(family: TemplateBlokNames) -> set[str]:
        """
        List the blok names one family reacts to.

        Args:
            family: Blok naming of a template family.

        Returns:
            The component names, without the optional about blok when the family has none.
        """
        names: set[str] = {
            family.hero,
            family.trust,
            family.gallery,
            family.reviews,
            family.contact,
        }
        if family.about:
            names.add(family.about)
        return names

    @staticmethod
    def _apply_rating(blok: dict[str, Any], rating_label: str, family: TemplateBlokNames) -> None:
        """
        Write the Google rating into the trust blok.

        The item whose label already mentions "avis" wins; otherwise the family decides whether the
        rating overwrites the first or the last item.

        Args:
            blok: Trust blok, mutated in place.
            rating_label: Formatted rating.
            family: Blok naming of the template family.
        """
        items = blok.get("items")
        if not isinstance(items, list) or not items:
            return
        for item in items:
            if isinstance(item, dict) and "avis" in str(item.get("label", "")).lower():
                item["value"] = rating_label
                return

        fallback = items[0] if family.rates_first_trust_item else items[-1]
        if isinstance(fallback, dict):
            fallback["value"] = rating_label
            fallback["label"] = GOOGLE_RATING_LABEL

    @staticmethod
    def _build_gallery_items(photos: list[str], family: TemplateBlokNames) -> list[dict[str, Any]]:
        """
        Build the gallery bloks from the scraped photos.

        Args:
            photos: Absolute photo URLs.
            family: Blok naming of the template family.

        Returns:
            One gallery item per photo, capped at ``MAX_GALLERY_PHOTOS``.
        """
        items: list[dict[str, Any]] = []
        for index, url in enumerate(photos[:MAX_GALLERY_PHOTOS]):
            item: dict[str, Any] = {
                "_uid": f"{family.uid_prefix}g-enriched-{index}",
                "component": family.gallery_item,
                "image": url,
                "caption": "",
            }
            if family.carries_location:
                item["location"] = ""
            items.append(item)
        return items

    @staticmethod
    def _build_review_items(reviews: list[dict], family: TemplateBlokNames) -> list[dict[str, Any]]:
        """
        Build the testimonial bloks from the scraped reviews.

        Args:
            reviews: Raw review dicts.
            family: Blok naming of the template family.

        Returns:
            One item per review that carries text, capped at ``MAX_REVIEWS``.
        """
        items: list[dict[str, Any]] = []
        for index, review in enumerate(reviews[:MAX_REVIEWS]):
            quote: str = str(review.get("text", "")).strip()
            if not quote:
                continue
            item: dict[str, Any] = {
                "_uid": f"{family.uid_prefix}r-enriched-{index}",
                "component": family.review_item,
                "quote": quote,
                "author": str(review.get("author", "Client")).strip() or "Client",
                "rating": (
                    int(review["rating"]) if isinstance(review.get("rating"), (int, float)) else DEFAULT_REVIEW_RATING
                ),
            }
            if family.carries_location:
                item["location"] = ""
            items.append(item)
        return items
