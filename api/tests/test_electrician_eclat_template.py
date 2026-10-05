"""
Tests for the 'electrician-eclat' template: its content must stay complete and honest for a prospect
with no enrichment at all, keep a prospect's own photos together, and expose in the client's editor
exactly the fields its layer renders.
"""

from typing import Any

from services.templates import electrician_eclat, registry
from services.templates.default_images import DEFAULT_IMAGES, apply_default_images

_PALETTE: dict[str, str] = {"primary": "#F59E0B", "secondary": "#0B1B2E", "accent": "#F59E0B"}


def _site(city: str | None = "Orléat", enrichment: dict[str, Any] | None = None) -> dict[str, Any]:
    return registry.build_site_content(
        template_id="electrician-eclat",
        business_name="Cz63 Électricité",
        phone="06 61 58 86 79",
        email="contact@example.fr",
        city=city,
        area=city or "votre secteur",
        subtitle=registry.default_subtitle("electrician-eclat", city or "votre secteur"),
        palette=_PALETTE,
        enrichment=enrichment,
    )


def _section_fields(body: list[dict[str, Any]], section: str) -> set[str]:
    blok = next(blok for blok in body if blok["component"] == f"section_{section}")
    return set(blok) - {"_uid", "component"}


def test_template_is_registered_before_the_older_electrician_template() -> None:
    """Éclat is offered first to electricians; Lumen stays available for comparison."""
    ids = [module.TEMPLATE_ID for module in registry.TEMPLATE_MODULES]
    assert ids.index("electrician-eclat") < ids.index("electrician-lumen")
    assert registry.brand_color_key("electrician-eclat") == "primary"


def test_content_is_complete_without_any_enrichment() -> None:
    """A bare prospect still gets a title, six illustrated services, the method, the FAQ and both extra photos."""
    site = _site()
    assert site["heroTitle"] == "Votre électricien de confiance à Orléat"
    assert len(site["services"]) == 6
    assert all(service["image"].startswith("https://images.unsplash.com/") for service in site["services"])
    assert len(site["steps"]) == 4
    assert len(site["faq"]) == 5
    assert site["images"]["heroSecondary"].startswith("https://images.unsplash.com/")
    assert site["images"]["ctaBackground"].startswith("https://images.unsplash.com/")


def test_copy_has_no_em_dash() -> None:
    """Site copy never uses an em dash (house style)."""
    site = _site()
    texts = [site["subtitle"], site["heroTitle"], site["servicesLead"], site["ctaLead"], site["contactLead"]]
    texts += [service["description"] for service in site["services"]]
    texts += [item["answer"] for item in site["faq"]]
    assert not any("—" in text for text in texts)


def test_rating_slot_shows_the_real_rating_or_a_neutral_claim() -> None:
    """The placeholder rating never reaches the site: the real Google rating replaces it, or « Devis gratuit »."""
    with_rating = [
        (item["value"], item["label"]) for item in _site(enrichment={"rating": 5.0, "reviews_count": 35})["trustItems"]
    ]
    assert ("5,0/5", "35 avis") in with_rating
    without_rating = [(item["value"], item["label"]) for item in _site()["trustItems"]]
    assert ("Devis gratuit", "Sans engagement") in without_rating
    assert "4,9/5" not in [value for value, _ in without_rating]


def test_small_hero_photo_is_left_to_the_layer_when_the_prospect_has_gallery_photos() -> None:
    """With gallery photos no stock photo is seeded: the layer shows the first gallery photo, whatever its order."""
    photos = [f"https://cdn.example.fr/chantier-{index}.jpg" for index in range(4)]
    site = _site(enrichment={"photos": photos})
    assert site["heroImage"] == photos[0]
    assert site["aboutImage"] == photos[1]
    assert site["gallery"][0]["url"] == photos[2]
    assert "heroSecondary" not in site["images"]


def test_default_images_fill_only_empty_slots() -> None:
    """Hero, about and gallery fall back to the template's photos; a real photo is never replaced."""
    site = _site()
    apply_default_images(site, "electrician-eclat")
    defaults = DEFAULT_IMAGES["electrician-eclat"]
    assert site["heroImage"] == defaults["heroImage"]
    assert site["aboutImage"] == defaults["aboutImage"]
    assert [photo["url"] for photo in site["gallery"]] == defaults["gallery"]

    own_photo = "https://cdn.example.fr/facade.jpg"
    enriched = _site(enrichment={"photos": [own_photo]})
    apply_default_images(enriched, "electrician-eclat")
    assert enriched["heroImage"] == own_photo


def test_title_contracts_the_article_of_the_city() -> None:
    """« à Le Mont-sur-Lausanne » reads « au Mont-sur-Lausanne »."""
    assert _site(city="Le Mont-sur-Lausanne")["heroTitle"] == "Votre électricien de confiance au Mont-sur-Lausanne"


def test_unknown_city_never_prints_the_placeholder() -> None:
    """Without a city the title has none, and the « votre secteur » placeholder is not stored as a city."""
    site = _site(city=None)
    assert site["heroTitle"] == "Votre électricien de confiance"
    assert site["city"] == ""
    assert site["subtitle"].endswith("garanti dans votre secteur.")


def test_generations_do_not_share_mutable_defaults() -> None:
    """Editing one generated site's lists must not leak into the next generation."""
    first = _site()
    first["heroPoints"].append("Ajout")
    first["faq"][0]["answer"] = "Modifié"
    first["steps"][0]["title"] = "Modifié"
    second = _site()
    assert "Ajout" not in second["heroPoints"]
    assert second["faq"][0]["answer"] == electrician_eclat.ECLAT_FAQ[0]["answer"]
    assert second["steps"][0]["title"] == "Premier contact"


def test_editor_shows_exactly_the_rendered_sections_and_fields() -> None:
    """The client's editor lists the nine rendered sections, with the editable title and both extra photos."""
    body = registry.to_storyblok_site_content("electrician-eclat", _site())
    assert [blok["component"] for blok in body] == [
        "section_hero",
        "section_trust",
        "section_about",
        "section_services",
        "section_method",
        "section_gallery",
        "section_reviews",
        "section_faq",
        "section_contact",
    ]
    hero_fields = _section_fields(body, "hero")
    assert {"heroTitle", "heroSecondary", "heroBadge", "heroPoints", "ctaQuoteLabel"} <= hero_fields
    assert "ctaCallLabel" not in hero_fields
    contact_fields = _section_fields(body, "contact")
    assert {"contactLead", "ctaTitle", "ctaLead", "ctaBackground"} <= contact_fields
    assert "servicesLead" in _section_fields(body, "services")
