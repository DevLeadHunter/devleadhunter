"""
Tests for the real trust badges — a template's stat badges must come from real data (satisfaction
from the Google rating, experience from the founding year, the review count) and never leak between
generations (the shared editorial defaults must not be mutated in place).
"""

from services.templates import registry
from services.templates.site_content import apply_real_trust_stats


def _barber_trust(enrichment: dict) -> list[tuple[str, str]]:
    site = registry.build_site_content(
        template_id="barber",
        business_name="X",
        phone="0",
        email="x@y.fr",
        city="Tours",
        area="Tours",
        subtitle="",
        palette={"primary": "#000", "secondary": "#111", "accent": "#222"},
        enrichment=enrichment,
    )
    return [(item["value"], item["label"]) for item in site["trustItems"]]


def test_satisfaction_is_derived_from_the_real_rating() -> None:
    """The 'satisfaction %' badge comes from the rating (4,9/5 → 98 %, 4,7/5 → 94 %), not a hardcoded value."""
    assert _barber_trust({"rating": 4.9, "reviews_count": 128, "description": "Salon depuis 2015"})[0] == (
        "98%",
        "Clients satisfaits",
    )
    assert _barber_trust({"rating": 4.7})[0] == ("94%", "Clients satisfaits")


def test_experience_uses_real_year_else_review_count() -> None:
    """Experience shows the real years ('depuis 20xx'); with no founding year it falls back to the review count."""
    assert _barber_trust({"rating": 4.9, "description": "Ouvert depuis 2015"})[1][0] == "11+"
    assert _barber_trust({"rating": 4.9, "reviews_count": 128})[1] == ("128", "avis Google")


def test_fabricated_defaults_replaced_by_neutral_claims_and_no_state_leak() -> None:
    """Without real figures the fabricated stats become neutral claims; a prior enriched call must not leak."""
    _barber_trust({"rating": 4.7, "reviews_count": 200})  # would mutate shared defaults if buggy
    assert _barber_trust({}) == [("Sur mesure", "Travail soigné"), ("Réactif", "Réponse rapide")]


def test_apply_real_trust_stats_does_not_mutate_input_items() -> None:
    """The helper returns fresh items and never mutates the caller's list in place."""
    original = [{"value": "98%", "label": "Clients satisfaits"}]
    site = {"trustItems": original, "about": ""}
    apply_real_trust_stats(site, {"rating": 4.6})
    assert original == [{"value": "98%", "label": "Clients satisfaits"}]
    assert site["trustItems"][0]["value"] == "92%"
