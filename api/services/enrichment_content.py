"""
Pure mapping of enrichment data into a template's content_json.

Kept dependency-free (no scrapers, no DB) so it can be imported by
``storyblok_service`` without pulling the heavy scraper import chain.
"""
from __future__ import annotations

import copy
from typing import Any, Optional


def format_rating(rating: Optional[float]) -> Optional[str]:
    """Format a numeric rating as "4,9/5" (French)."""
    if rating is None:
        return None
    try:
        return f"{float(rating):.1f}".replace(".", ",") + "/5"
    except (TypeError, ValueError):
        return None


def format_hours(hours: Optional[list]) -> Optional[str]:
    """Build a one-line opening-hours string from structured rows."""
    if not hours:
        return None
    parts: list[str] = []
    for row in hours:
        if isinstance(row, dict) and row.get("day") and row.get("hours"):
            parts.append(f"{row['day']} {row['hours']}")
    return " · ".join(parts) if parts else None


def apply_to_content(
    content_json: dict[str, Any], enrichment: Optional[dict[str, Any]]
) -> dict[str, Any]:
    """
    Merge enrichment data into a template's content_json.

    Template-agnostic: only fills bloks that exist in the content. Photos feed the
    hero image and gallery, reviews feed testimonials, rating feeds the trust
    block, opening hours feed the contact block.
    """
    if not enrichment or not isinstance(content_json, dict):
        return content_json

    content = copy.deepcopy(content_json)
    body = content.get("body")
    if not isinstance(body, list):
        return content

    photos: list[str] = [p for p in enrichment.get("photos", []) if isinstance(p, str)]
    reviews: list[dict] = [r for r in enrichment.get("reviews", []) if isinstance(r, dict)]
    rating_label = format_rating(enrichment.get("rating"))
    hours_label = format_hours(enrichment.get("opening_hours"))

    for blok in body:
        if not isinstance(blok, dict):
            continue
        component = blok.get("component")

        if component == "hero" and photos:
            blok["image"] = photos[0]

        elif component == "trust" and rating_label:
            items = blok.get("items")
            if isinstance(items, list):
                matched = False
                for item in items:
                    if isinstance(item, dict) and "avis" in str(item.get("label", "")).lower():
                        item["value"] = rating_label
                        matched = True
                        break
                if not matched and items:
                    first = items[0]
                    if isinstance(first, dict):
                        first["value"] = rating_label
                        first["label"] = "Avis Google"

        elif component == "gallery" and photos:
            blok["items"] = [
                {
                    "_uid": f"g-enriched-{i}",
                    "component": "gallery_item",
                    "image": url,
                    "caption": "",
                    "location": "",
                }
                for i, url in enumerate(photos[:8])
            ]

        elif component == "testimonials" and reviews:
            mapped = [
                {
                    "_uid": f"r-enriched-{i}",
                    "component": "testimonial_item",
                    "quote": str(review.get("text", "")).strip(),
                    "author": str(review.get("author", "Client")).strip() or "Client",
                    "location": "",
                    "rating": int(review["rating"]) if isinstance(review.get("rating"), (int, float)) else 5,
                }
                for i, review in enumerate(reviews[:6])
                if str(review.get("text", "")).strip()
            ]
            if mapped:
                blok["items"] = mapped

        elif component == "contact" and hours_label:
            blok["hours"] = hours_label

        # --- 'electrician-lumen' namespaced bloks (additive, other templates untouched) ---

        elif component == "lumen_hero" and photos:
            blok["image"] = photos[0]

        elif component == "lumen_trust" and rating_label:
            items = blok.get("items")
            if isinstance(items, list) and items:
                matched = False
                for item in items:
                    if isinstance(item, dict) and "avis" in str(item.get("label", "")).lower():
                        item["value"] = rating_label
                        matched = True
                        break
                if not matched:
                    last = items[-1]
                    if isinstance(last, dict):
                        last["value"] = rating_label
                        last["label"] = "Avis Google"

        elif component == "lumen_gallery" and photos:
            blok["items"] = [
                {
                    "_uid": f"lumen-g-enriched-{i}",
                    "component": "lumen_gallery_item",
                    "image": url,
                    "caption": "",
                }
                for i, url in enumerate(photos[:8])
            ]

        elif component == "lumen_reviews" and reviews:
            mapped = [
                {
                    "_uid": f"lumen-r-enriched-{i}",
                    "component": "lumen_review_item",
                    "quote": str(review.get("text", "")).strip(),
                    "author": str(review.get("author", "Client")).strip() or "Client",
                    "rating": int(review["rating"]) if isinstance(review.get("rating"), (int, float)) else 5,
                }
                for i, review in enumerate(reviews[:6])
                if str(review.get("text", "")).strip()
            ]
            if mapped:
                blok["items"] = mapped

        elif component == "lumen_contact" and hours_label:
            blok["hours"] = hours_label

        # --- 'plumber-cuivre' namespaced bloks (additive, other templates untouched) ---

        elif component == "cuivre_hero" and photos:
            blok["image"] = photos[0]

        elif component == "cuivre_trust" and rating_label:
            items = blok.get("items")
            if isinstance(items, list) and items:
                matched = False
                for item in items:
                    if isinstance(item, dict) and "avis" in str(item.get("label", "")).lower():
                        item["value"] = rating_label
                        matched = True
                        break
                if not matched:
                    last = items[-1]
                    if isinstance(last, dict):
                        last["value"] = rating_label
                        last["label"] = "Avis Google"

        elif component == "cuivre_about" and len(photos) > 1:
            blok["image"] = photos[1]

        elif component == "cuivre_gallery" and photos:
            blok["items"] = [
                {
                    "_uid": f"cuivre-g-enriched-{i}",
                    "component": "cuivre_gallery_item",
                    "image": url,
                    "caption": "",
                }
                for i, url in enumerate(photos[:8])
            ]

        elif component == "cuivre_reviews" and reviews:
            mapped = [
                {
                    "_uid": f"cuivre-r-enriched-{i}",
                    "component": "cuivre_review_item",
                    "quote": str(review.get("text", "")).strip(),
                    "author": str(review.get("author", "Client")).strip() or "Client",
                    "rating": int(review["rating"]) if isinstance(review.get("rating"), (int, float)) else 5,
                }
                for i, review in enumerate(reviews[:6])
                if str(review.get("text", "")).strip()
            ]
            if mapped:
                blok["items"] = mapped

        elif component == "cuivre_contact" and hours_label:
            blok["hours"] = hours_label

    return content
