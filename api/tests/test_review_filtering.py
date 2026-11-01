"""
Tests for review curation on the generated site: a sales site must surface only reviews we are sure
are positive (rating >= 4). Complaints (rating < 4) and reviews whose per-review rating wasn't
captured are dropped — the enrichment record keeps every review, but the site does not show them.
"""

from services.templates import registry


def _site_reviews(enrichment: dict) -> list[dict]:
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
    return site["reviews"]


def test_only_positive_reviews_reach_the_site() -> None:
    """Ratings >= 4 are kept, in order; a 1-star complaint and a 3-star are dropped."""
    reviews = _site_reviews(
        {
            "reviews": [
                {"author": "A", "text": "Top", "rating": 5},
                {"author": "B", "text": "Travaux sans accord", "rating": 1},
                {"author": "C", "text": "Bien", "rating": 4},
                {"author": "D", "text": "Moyen", "rating": 3},
            ]
        }
    )
    assert [r["author"] for r in reviews] == ["A", "C"]
    assert all(r["rating"] >= 4 for r in reviews)


def test_reviews_without_a_rating_or_text_are_dropped() -> None:
    """No captured rating -> dropped (can't be trusted as positive); empty text -> dropped."""
    reviews = _site_reviews(
        {
            "reviews": [
                {"author": "A", "text": "Super", "rating": 5},
                {"author": "NoRating", "text": "Sans note"},
                {"author": "Empty", "text": "", "rating": 5},
            ]
        }
    )
    assert [r["author"] for r in reviews] == ["A"]


def test_duplicate_reviews_are_shown_once() -> None:
    """Same (author, text) captured twice -> shown once. Older enrichment predates scrape-time dedup."""
    reviews = _site_reviews(
        {
            "reviews": [
                {"author": "Marie L.", "text": "Super salon", "rating": 5},
                {"author": "marie l.", "text": "super salon", "rating": 5},  # same review, different case
                {"author": "Marie L.", "text": "Autre visite tout aussi top", "rating": 5},
            ]
        }
    )
    assert [r["text"] for r in reviews] == ["Super salon", "Autre visite tout aussi top"]


def test_a_five_star_complaint_stays_off_the_site_but_not_disappointed_is_praise() -> None:
    """Stars do not make praise: a disappointed 5-star text is dropped, « pas déçu » is kept."""
    reviews = _site_reviews(
        {
            "reviews": [
                {
                    "author": "Vanessa",
                    "text": "De très bon conseil. En ce qui concerne mon projet, je suis un peu déçue car il ne "
                    "répond plus aux messages... Je vais à regrets devoir me tourner vers un autre professionnel",
                    "rating": 5,
                },
                {"author": "Theo", "text": "Jamais déçu, véhicule livré dans les temps.", "rating": 5},
                {"author": "Lea", "text": "Vous ne serez pas déçus, je recommande.", "rating": 5},
                {"author": "Paul", "text": "Garage à éviter, aucune réponse au devis.", "rating": 4},
            ]
        }
    )
    assert [r["author"] for r in reviews] == ["Theo", "Lea"]
