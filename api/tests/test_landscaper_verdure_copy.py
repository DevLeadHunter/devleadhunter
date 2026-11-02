"""
Rule n° 1 of the demo sites: nothing made up. Before anyone writes a landscaper's own texts, its generated site
promises nothing the business never said (free quote, answer within 48 h, insurance, guarantee, a lone craftsman),
and the « À propos » ticks come from the strengths written for it, which its client edits in the CMS.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

from services.storyblok_service import storyblok_service
from services.templates import registry
from services.templates.site_content import from_storyblok_site_content, overrides_from_published_story

_UNPROVEN_PROMISE = re.compile(r"gratuit|48 ?h|assur|garanti|certifi|sans engagement|un seul artisan", re.IGNORECASE)


def _generated_site(enrichment: dict[str, Any] | None = None) -> dict[str, Any]:
    """A landscaper site as generated, before any text is written for the business."""
    return storyblok_service.build_content_json(
        business_name="Les Jardins du Locle",
        phone="032 931 00 00",
        email="contact@example.com",
        city="Le Locle",
        description=None,
        template_id="landscaper-verdure",
        enrichment=enrichment,
    )


@pytest.mark.parametrize("enrichment", [None, {"rating": 4.8, "reviews_count": 23}])
def test_a_generated_landscaper_site_promises_nothing_unproven(enrichment: dict[str, Any] | None) -> None:
    site = _generated_site(enrichment)

    assert _UNPROVEN_PROMISE.findall(json.dumps(site, ensure_ascii=False)) == []


def test_the_strengths_written_for_a_landscaper_reach_its_cms_and_survive_a_publish() -> None:
    written: dict[str, Any] = {
        "strengths": [{"title": "Jardinier composteur", "description": ""}],
        "contactLead": "Appelez-moi ou laissez vos coordonnées : je vous rappelle pour en parler.",
    }
    story: dict[str, Any] = {
        "component": "page",
        "body": registry.to_storyblok_site_content("landscaper-verdure", {"businessName": "Tistou", **written}),
    }

    strengths = next(blok for blok in story["body"] if blok["component"] == "section_strengths")
    assert [item["title"] for item in strengths["strengths"]] == ["Jardinier composteur"]
    assert "strengthsHeading" not in strengths
    assert overrides_from_published_story(written, story, from_storyblok_site_content(story)) == written
