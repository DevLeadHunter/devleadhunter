"""Generated site content written for the prospect's country: Québec words, local phone shape."""

from __future__ import annotations

from services.templates.site_content import apply_country_conventions


def _site() -> dict:
    return {
        "businessName": "Devis Express Inc.",
        "phone": "5145550199",
        "email": "devis@devis-express.ca",
        "address": "123, rue Sainte-Catherine Ouest",
        "city": "Montréal",
        "area": "Montréal et ses alentours",
        "subtitle": "Un devis gratuit par e-mail sous 48 h.",
        "about": "Je réponds à chaque demande de devis depuis mon portable.",
        "ctaQuoteLabel": "Demander un devis",
        "heroImage": "https://img.example/devis-hero.jpg",
        "gallery": [{"url": "https://img.example/g1.jpg", "alt": "Devis en cours"}],
        "services": [{"title": "Devis détaillé", "description": "Chiffrage précis par e-mail."}],
        "faq": [{"question": "Le devis est-il gratuit ?", "answer": "Oui, le devis est gratuit."}],
        "reviews": [{"author": "Marie", "text": "Devis rapide, super portable.", "rating": 5}],
        "social": [{"network": "facebook", "url": "https://facebook.com/devis-express"}],
        "palette": {"primary": "#111", "secondary": "#fff", "accent": "#f90"},
    }


def test_quebec_site_reads_quebec_words_and_phone() -> None:
    site = apply_country_conventions(_site(), "CA")
    assert site["phone"] == "514 555-0199"
    assert site["subtitle"] == "Une soumission gratuite par courriel sous 48 h."
    assert site["about"] == "Je réponds à chaque demande de soumission depuis mon cellulaire."
    assert site["ctaQuoteLabel"] == "Demander une soumission"
    assert site["services"] == [{"title": "Soumission détaillée", "description": "Chiffrage précis par courriel."}]
    assert site["faq"] == [
        {"question": "La soumission est-elle gratuite ?", "answer": "Oui, la soumission est gratuite."}
    ]
    assert site["gallery"] == [{"url": "https://img.example/g1.jpg", "alt": "Soumission en cours"}]


def test_identity_contact_media_and_real_reviews_stay_verbatim() -> None:
    site = apply_country_conventions(_site(), "CA")
    assert site["businessName"] == "Devis Express Inc."
    assert site["email"] == "devis@devis-express.ca"
    assert site["address"] == "123, rue Sainte-Catherine Ouest"
    assert site["heroImage"] == "https://img.example/devis-hero.jpg"
    assert site["reviews"] == [{"author": "Marie", "text": "Devis rapide, super portable.", "rating": 5}]
    assert site["social"] == [{"network": "facebook", "url": "https://facebook.com/devis-express"}]


def test_a_french_site_only_gets_its_phone_shaped() -> None:
    original = _site()
    original["phone"] = "+33612345678"
    site = apply_country_conventions(original, "FR")
    assert site["phone"] == "06 12 34 56 78"
    assert site["subtitle"] == original["subtitle"]
    assert site["services"] == original["services"]


def test_the_input_content_is_never_mutated() -> None:
    """Templates share their editorial defaults: localizing one site must not rewrite the next one."""
    original = _site()
    nested_before = original["services"][0]["title"]
    apply_country_conventions(original, "CA")
    assert original["phone"] == "5145550199"
    assert original["subtitle"] == "Un devis gratuit par e-mail sous 48 h."
    assert original["services"][0]["title"] == nested_before == "Devis détaillé"
