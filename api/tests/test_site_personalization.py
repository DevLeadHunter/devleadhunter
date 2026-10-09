"""
Automatic personalisation of a demo site: the model's answer is checked before it reaches the site.

Only the business's showable photos take a slot (a flyer, a customer or a photo with added text never takes the hero),
each photo is used once, texts are tidied and cut where they still read whole, a promise the data never makes is
dropped, and the badge, the facts under the title and the rating sentence are computed from the data.
"""

from __future__ import annotations

import pytest

from services.photo_labels import PHOTO_FAMILY_CRAFT, normalize_craft_label
from services.site_personalization_service import (
    BusinessFacts,
    TemplatePersonalizationProfile,
    assemble_personalization,
    build_hero_sentence,
    clean_copy,
    hero_badge,
    hero_points,
    praise_sentence,
    profile_for_template,
    without_unsupported_claims,
)


def _label(kind: str, description: str = "", *, text: bool = False, appeal: int = 4) -> dict:
    label = normalize_craft_label(
        {"kind": kind, "description": description, "services": [], "texte": text, "appeal": appeal}
    )
    assert label is not None and label["family"] == PHOTO_FAMILY_CRAFT
    return label


def _facts(**overrides: object) -> BusinessFacts:
    values: dict[str, object] = {
        "business_name": "Jardins Exemple",
        "trade": "paysagiste",
        "city": "Gland",
        "country": "CH",
        "description": "Création et entretien de jardins, taille de haies.",
        "services_listed": ["Taille de haies"],
        "reviews": ["Travail soigné, haie impeccable.", "Très bon contact, chantier propre."],
        "rating": 4.8,
        "reviews_count": 23,
    }
    values.update(overrides)
    return BusinessFacts(**values)


_PROFILE = TemplatePersonalizationProfile(
    default_cards=[
        {"title": "Création de jardins", "description": "Un jardin pensé pour vous."},
        {"title": "Entretien & tonte", "description": "Un jardin entretenu toute l'année."},
        {"title": "Terrasses & allées", "description": "Des extérieurs praticables."},
        {"title": "Arrosage & clôtures", "description": "Un jardin arrosé et fermé."},
    ],
    portfolio_count=2,
    image_slots={"ctaBackground": "Image de fond de la bannière contact"},
    hero_kinds=("work", "premises", "team"),
)


def test_a_text_too_long_is_cut_at_a_comma_and_never_on_a_dangling_word() -> None:
    assert clean_copy("Taille de haies, tonte de pelouse et entretien régulier du jardin", 50) == (
        "Taille de haies, tonte de pelouse et entretien."
    )
    assert (
        clean_copy("Pose de clôtures en bois et en métal avec des portails", 40)
        == "Pose de clôtures en bois et en métal."
    )
    assert clean_copy("Création de jardins — sur mesure ! 🌿", 80) == "Création de jardins, sur mesure."


def test_a_title_is_cut_without_a_full_stop() -> None:
    title = clean_copy(
        "Jardin en pente aménagé avec des jeunes plants alignés, des arbustes et des fleurs", 80, is_sentence=False
    )

    assert title == "Jardin en pente aménagé avec des jeunes plants alignés"


def test_a_sentence_promising_what_the_data_never_says_is_dropped() -> None:
    corpus = "taille de haies, devis gratuit sur place."
    text = "Je taille vos haies. Le devis est gratuit. Travail garanti 10 ans. Intervention rapide."

    assert without_unsupported_claims(text, corpus) == "Je taille vos haies. Le devis est gratuit."


def test_the_hero_sentence_is_built_from_the_trade_and_drops_services_until_it_fits() -> None:
    corpus = "taille de haies"
    services = ["Taille de haies", "pose de clôtures en bois et en métal", "aménagement de jardins méditerranéens"]

    sentence = build_hero_sentence("paysagiste", "Saint-Jean-sur-Richelieu", services, corpus)

    assert sentence == "Paysagiste à Saint-Jean-sur-Richelieu : taille de haies, pose de clôtures en bois et en métal."
    assert build_hero_sentence("", "Gland", services, corpus) == ""
    assert build_hero_sentence("Paysagiste", "Gland", ["entretien gratuit"], corpus) == ""


def test_the_badge_points_and_praise_come_from_the_data() -> None:
    facts = _facts(description="Entreprise familiale depuis 2009.")

    assert hero_badge(facts) == "Paysagiste à Gland"
    points = hero_points(facts, ["Une prestation au titre bien trop long", "Taille de haies"])
    assert points[0] == "4,8/5 sur 23 avis Google"
    assert points[2] == "Gland et alentours"
    assert "Taille de haies" not in points
    assert praise_sentence(facts) == "Nos clients nous donnent 4,8 sur 5 sur Google."
    assert praise_sentence(_facts(boss_first_name="Alex", boss_last_name="Martin")).startswith("Mes clients me")
    assert praise_sentence(_facts(rating=4.9, reviews_count=3)) == ""
    assert hero_points(_facts(rating=4.2), ["Taille de haies"]) == ["Gland et alentours", "Taille de haies"]


def test_only_showable_photos_without_added_text_take_the_hero_and_the_slots() -> None:
    labels = {
        "flyer": _label("logo_or_flyer", "Carte de vœux"),
        "caption": _label("work", "Haie taillée avec une légende", text=True, appeal=5),
        "garden": _label("work", "Jardin avec allée en graviers"),
        "team": _label("team", "Le patron taille une haie"),
        "fence": _label("work", "Clôture en bois posée"),
        "terrace": _label("work", "Terrasse en dalles"),
    }
    pool = ["flyer", "caption", "garden", "team", "fence", "terrace"]
    inventory = [url for url in pool if url != "flyer"]
    answer = {
        "accroche_metier": "Paysagiste",
        "accroche_prestations": ["taille de haies", "pose de clôtures"],
        "a_propos": "Nous entretenons les jardins de Gland. Nos clients aiment le travail soigné.",
        "photo_entete": inventory.index("caption") + 1,
        "photo_a_propos": inventory.index("team") + 1,
        "prestations": [
            {"titre": "Taille de haies", "description": "Des haies nettes.", "photo": inventory.index("caption") + 1},
            {
                "titre": "Pose de clôtures",
                "description": "Des clôtures solides.",
                "photo": inventory.index("fence") + 1,
            },
        ],
        "realisations": [{"photo": inventory.index("terrace") + 1, "categorie": "Terrasse"}],
        "emplacements": {"ctaBackground": inventory.index("caption") + 1},
    }

    result = assemble_personalization(
        answer, facts=_facts(), profile=_PROFILE, pool=pool, labels=labels, inventory=inventory
    )

    assert result.photo_order[:2] == ["garden", "team"]
    assert "flyer" not in result.photo_order
    assert [card["image"] for card in result.service_cards[:2]] == ["caption", "fence"]
    assert len(result.service_cards) == 4
    assert result.service_cards[2]["title"] == "Création de jardins"
    assert result.portfolio == [{"image": "terrace", "title": "Terrasse en dalles", "category": "Terrasse"}]
    assert "caption" not in result.section_images.values()
    assert result.hero_sentence == "Paysagiste à Gland : taille de haies, pose de clôtures."
    assert result.about.endswith("Nos clients nous donnent 4,8 sur 5 sur Google.")
    assert result.hero_badge == "Paysagiste à Gland"


def test_without_reviews_the_about_says_nothing_of_the_customers() -> None:
    labels = {"garden": _label("work", "Jardin")}
    answer = {"a_propos": "Nous entretenons les jardins de Gland. Nos clients aiment notre travail."}

    result = assemble_personalization(
        answer,
        facts=_facts(reviews=[], rating=None, reviews_count=None),
        profile=_PROFILE,
        pool=["garden"],
        labels=labels,
        inventory=["garden"],
    )

    assert result.about == "Nous entretenons les jardins de Gland."


def test_a_quebec_business_reads_its_own_words() -> None:
    labels = {"panel": _label("work", "Tableau électrique neuf")}
    answer = {
        "accroche_metier": "Électricien",
        "accroche_prestations": ["tableau électrique", "éclairage"],
        "prestations": [{"titre": "Tableau électrique", "description": "Un tableau électrique neuf.", "photo": 1}],
    }

    result = assemble_personalization(
        answer,
        facts=_facts(trade="électricien", city="Laval", country="CA", description="Tableau électrique"),
        profile=_PROFILE,
        pool=["panel"],
        labels=labels,
        inventory=["panel"],
    )

    assert "panneau électrique" in result.hero_sentence
    assert result.service_cards[0]["title"] == "Panneau électrique"


@pytest.mark.parametrize("template_id", ["landscaper-verdure", "mechanic-pitlane", "electrician-eclat"])
def test_a_template_profile_lists_its_cards_realizations_and_photo_slots(template_id: str) -> None:
    profile = profile_for_template(template_id)

    assert len(profile.default_cards) >= 3
    assert all(card["title"] and card["description"] for card in profile.default_cards)
    assert profile.image_slots
    assert profile.portfolio_count == (2 if template_id == "landscaper-verdure" else 0)
