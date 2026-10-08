"""
Tests for the fragmentary-about guard: a description assembled from scraped attribute fragments
("Food Truck à Poitiers Spécialité: poulet frit coréen") reads badly and must be rejected in favour
of a clean template default. Real prose — even long prose mentioning a specialty — is left alone.
"""

from services.templates import registry
from services.validation_service import validation_service


def test_scraped_attribute_fragments_are_flagged() -> None:
    assert validation_service.is_fragmentary_description("Food Truck à Poitiers Spécialité: poulet frit coréen")
    assert validation_service.is_fragmentary_description("Garage Catégorie: Réparation automobile")


def test_real_prose_is_not_flagged() -> None:
    assert not validation_service.is_fragmentary_description(
        "Le salon Barbier d'Antan vous accueille dans une ambiance chic et élégante inspirée des années 30."
    )
    # lowercase 'spécialité' in a sentence is prose, not a scraped label
    assert not validation_service.is_fragmentary_description(
        "Notre spécialité, c'est le poulet frit coréen préparé minute avec des produits frais."
    )
    assert not validation_service.is_fragmentary_description(None)
    assert not validation_service.is_fragmentary_description("")


def test_site_falls_back_to_default_when_about_is_fragmentary() -> None:
    site = registry.build_site_content(
        template_id="barber",
        business_name="X",
        phone="0",
        email="x@y.fr",
        city="Tours",
        area="Tours",
        subtitle="",
        palette={"primary": "#000", "secondary": "#111", "accent": "#222"},
        enrichment={"description": "Food Truck à Poitiers Spécialité: poulet frit coréen"},
    )
    assert "Spécialité:" not in site["about"]
    assert site["about"].strip()


def test_a_page_bio_or_a_contact_card_is_flagged() -> None:
    """Three wave 4 test sites showed their raw page bio as « À propos » (8 Oct 2026)."""
    assert validation_service.is_scraped_bio(
        "Jules et Paul Exemple Paysagiste 🌿 Aménagements de jardins 🌴 Entretien 🌱"
    )
    assert validation_service.is_scraped_bio("Entrepreneur en électricité 514-555-0199 Jules Exemple")
    assert validation_service.is_scraped_bio(
        "Route Exemple 12 , 1000 Ville contact@exemple.ch Entretiens, réparations, changement de pneus."
    )


def test_prose_is_not_a_scraped_bio() -> None:
    assert not validation_service.is_scraped_bio(
        "Je crée et j'entretiens les jardins de la région depuis dix ans, avec le même soin du détail."
    )
    assert not validation_service.is_scraped_bio("Garage familial à Exempleville, ouvert en 1998 à la rue 12 1000.")
    assert not validation_service.is_scraped_bio(
        "Notre équipe intervient pour la création, l'entretien et la rénovation de vos espaces verts, "
        "particuliers comme professionnels, dans tout le canton. Nous préparons chaque chantier avec vous, "
        "du premier conseil au dernier coup de taille, et nous répondons au 021 555 01 99 du lundi au samedi."
    )
    assert not validation_service.is_scraped_bio(None)


def test_site_falls_back_to_default_when_about_is_a_page_bio() -> None:
    site = registry.build_site_content(
        template_id="landscaper-verdure",
        business_name="Exemple Jardins",
        phone="0",
        email="x@y.fr",
        city="Tours",
        area="Tours",
        subtitle="",
        palette={"primary": "#000", "secondary": "#111", "accent": "#222"},
        enrichment={"description": "Jules Exemple Paysagiste 🌿 Entretien 🌱 Création 🌴"},
    )
    assert "🌿" not in site["about"]
    assert site["about"].strip()
