"""Unit tests for the Facebook enrichment parsers — pure functions, no browser."""

from scrappers.facebook_enrichment_scraper import (
    FacebookEnrichmentScraper,
    _clean_social_url,
    _dedupe_photos,
    _parse_about_stats,
    _parse_bio_from_embedded_texts,
    _parse_intro_description,
    _parse_og_description,
    _parse_reviews,
    _parse_reviews_from_embedded_texts,
    _rating_from_pct,
    photo_identity,
)

# Real text captured from a public Facebook page's « À propos » panel.
_ABOUT_TEXT = """Food truck mexicain Tacos Maru
1,7 K followers • 2,1 K suivi(e)s
À propos
Coordonnées
., Châtellerault, France, 86100
Adresse
06 29 34 58 99
Mobile
+33 6 14 92 78 16
WhatsApp
foodtruckmexicaintacosmaru@gmail.com
E-mail
Recommandé par 96 % (22 avis)
Fourchette de prix · €€"""

# Intro card text from the public page home (not the polished marketing rewrite).
_INTRO_TEXT = """Intro
Food Truck Mexicain Tacos Maru C’est un Food Truck qui vous fait découvrir les spécialités et saveurs mexicaines.
Des recettes faites maison dans les traditions du Mexique
Qui apportant les saveurs traditionnelles, faite de manière artisanale
Page · Food truck
06 29 34 58 99
+33 6 14 92 78 16
Foodtruckmexicaintacosmaru@gmail.com
tiktok.com/@food.truck.mexicai
instagram.com/food_truck_mexicano_tacos_maru
facebook.com/TacosMexicanosMaru
Sièges en terrasse
Recommandé par 96 % (22 avis)"""

_OG_DESCRIPTION = (
    "Food truck mexicain Tacos Maru, Châtellerault. 1 720 J’aime · 17 en parlent. "
    "Food Truck Mexicain Tacos Maru  C’est un Food Truck qui vous fait découvrir "
    "les spécialités et saveurs mexicaines. Des recettes faites maison..."
)

# Real text captured from the same page's « Avis » panel (several reviews after login dismiss + scroll).
_REVIEWS_TEXT = """Recommandé par 96 % (22 avis)
Fox Emmanuel  recommande Food truck mexicain Tacos Maru.
27 septembre 2025
·
Copieux et délicieux on n'en demande pas plus et ça fait passer une très bonne soirée
Merci beaucoup
Plats excellents
Toutes les réactions :
1
Marie Breton  recommande Food truck mexicain Tacos Maru.
14 août 2025
·
Dégustation de 4 tacos si bons....!!! Assaisonnement parfait qui fait voyager instantanément.
Plats excellents
Toutes les réactions :
2
Guillaume Fournier  recommande Food truck mexicain Tacos Maru.
30 août 2023
·
Des plats tous aussi bons les un que les autres, du personnel au top du top !
Plats excellents
Toutes les réactions :
1
Mélissa Lambelin  ne recommande pas Food truck mexicain Tacos Maru.
1 janvier 2024
·
Pas convaincue
Toutes les réactions :
0"""

# Relay JSON often lists the body before the « X recommande » header — mirrors live HTML order.
_EMBEDDED_TEXTS = [
    "Recommandé par 96 % (22 avis)",
    "Copieux et délicieux on n'en demande pas plus et ça fait passer une très bonne soirée\nMerci beaucoup",
    "Fox Emmanuel  recommande Food truck mexicain Tacos Maru.",
    "Les commentaires ont été désactivés pour cette publication.",
    "Dégustation de 4 tacos si bons....!!! Assaisonnement parfait qui fait voyager instantanément. Jamais goûté de si délicieux tacos.",
    "Marie Breton  recommande Food truck mexicain Tacos Maru.",
    "Des plats tous aussi bons les un que les autres, du personnel au top du top !",
    "Guillaume Fournier  recommande Food truck mexicain Tacos Maru.",
]

_PAGE_EMBEDDED_BIO = [
    "1,7 K followers",
    "Food Truck Mexicain Tacos Maru  C’est un Food Truck qui vous fait découvrir les spécialités et saveurs mexicaines. \nDes recettes faites maison dans les traditions du Mexique\nQui apportant les saveurs traditionnelles, faite de manière artisanale",
    "Page · Food truck",
]


def test_rating_from_pct_converts_and_clamps() -> None:
    """A recommendation rate maps to /5, clamped to [0, 5]; None stays None."""
    assert _rating_from_pct(96) == 4.8
    assert _rating_from_pct(100) == 5.0
    assert _rating_from_pct(0) == 0.0
    assert _rating_from_pct(120) == 5.0
    assert _rating_from_pct(None) is None


def test_parse_about_stats_reads_rate_and_count() -> None:
    """« Recommandé par 96 % (22 avis) » yields (96, 22)."""
    assert _parse_about_stats(_ABOUT_TEXT) == (96, 22)


def test_parse_intro_description_keeps_blurb_and_stops_at_contacts() -> None:
    """Intro text is kept; category / phone / socials are stripped."""
    description = _parse_intro_description(_INTRO_TEXT)
    assert description is not None
    assert "spécialités et saveurs mexicaines" in description
    assert "faite de manière artisanale" in description
    assert "Page ·" not in description
    assert "06 29" not in description
    assert "instagram.com" not in description


def test_parse_og_description_strips_likes_prefix() -> None:
    """og:description drops the « X J'aime · Y en parlent » prefix."""
    description = _parse_og_description(_OG_DESCRIPTION)
    assert description is not None
    assert "J’aime" not in description
    assert "spécialités et saveurs mexicaines" in description


def test_parse_og_description_strips_bare_likes_prefix() -> None:
    """« {name}. {X} J'aime. {category} » (no « en parlent ») is stripped; weak pages return None."""
    # Weak page: nothing but name + likes + category survives → drop it (better empty than noise).
    assert _parse_og_description("Sawadee Thaï Foodtruck. 1 795 J’aime. Produit/service") is None
    # Real copy after the likes prefix is kept, and the « X J'aime » noise is gone.
    kept = _parse_og_description("Tasty Korea. 4 J’aime. Food Truck à Poitiers, spécialité poulet frit coréen")
    assert kept is not None
    assert "J’aime" not in kept
    assert "poulet frit coréen" in kept


def test_parse_bio_from_embedded_texts_keeps_full_intro() -> None:
    """Relay page-bio text is preferred when og:description is truncated."""
    bio = _parse_bio_from_embedded_texts(_PAGE_EMBEDDED_BIO)
    assert bio is not None
    assert "faite de manière artisanale" in bio
    assert "followers" not in bio.lower()


def test_parse_reviews_extracts_multiple_authors_and_bodies() -> None:
    """Several reviews keep author + body, drop dates and reaction footers."""
    reviews = _parse_reviews(_REVIEWS_TEXT)
    assert len(reviews) == 4
    assert reviews[0]["author"] == "Fox Emmanuel"
    assert reviews[0]["rating"] == 5
    assert "Copieux et délicieux" in reviews[0]["text"]
    assert "Plats excellents" in reviews[0]["text"]
    assert "27 septembre 2025" not in reviews[0]["text"]
    assert "Toutes les réactions" not in reviews[0]["text"]
    assert reviews[1]["author"] == "Marie Breton"
    assert "Assaisonnement parfait" in reviews[1]["text"]
    assert reviews[2]["author"] == "Guillaume Fournier"
    assert reviews[3]["author"] == "Mélissa Lambelin"
    assert reviews[3]["rating"] == 2


def test_parse_reviews_from_embedded_texts_pairs_headers_with_bodies() -> None:
    """Embedded Relay texts yield multiple reviews even when the DOM shows one."""
    reviews = _parse_reviews_from_embedded_texts(_EMBEDDED_TEXTS)
    assert len(reviews) >= 3
    authors = {review["author"] for review in reviews}
    assert "Fox Emmanuel" in authors
    assert "Marie Breton" in authors
    assert "Guillaume Fournier" in authors
    marie = next(review for review in reviews if review["author"] == "Marie Breton")
    assert "Assaisonnement parfait" in marie["text"]


def test_parse_reviews_marks_a_non_recommendation_lower() -> None:
    """« ne recommande pas » is a negative signal (2/5, not 5/5)."""
    text = (
        "Paul ne recommande pas Food truck mexicain Tacos Maru.\n"
        "1 janvier 2025\n"
        "À éviter vraiment\n"
        "Toutes les réactions :"
    )
    reviews = _parse_reviews(text)
    assert len(reviews) == 1
    assert reviews[0]["author"] == "Paul"
    assert reviews[0]["rating"] == 2


def test_dedupe_photos_drops_static_ui_icons() -> None:
    """UI glyphs on static.xx.fbcdn / rsrc.php must not enter the photo list."""
    photos = _dedupe_photos(
        [
            "https://static.xx.fbcdn.net/rsrc.php/yL/r/VLNVMYsRNQ9.webp",
            "https://scontent.xx.fbcdn.net/v/t39.30808-6/photo.jpg",
            "https://scontent.xx.fbcdn.net/v/t39.30808-6/photo.jpg",
            "https://scontent.xx.fbcdn.net/v/t39.30808-6/taco.jpg",
        ]
    )
    assert photos == [
        "https://scontent.xx.fbcdn.net/v/t39.30808-6/photo.jpg",
        "https://scontent.xx.fbcdn.net/v/t39.30808-6/taco.jpg",
    ]


def test_dedupe_photos_collapses_same_image_across_sizes() -> None:
    """One Facebook photo served at many sizes / CDN nodes / params dedupes to one via its numeric id."""
    same_a = "https://scontent-cdg6-1.xx.fbcdn.net/v/t39.30808-6/556857573_122106_n.jpg?stp=s600x600&_nc_ohc=A"
    same_b = "https://scontent-cdg2-1.xx.fbcdn.net/v/t39.30808-6/556857573_122106_n.jpg?stp=p1080x1080&_nc_ohc=B"
    other = "https://scontent-cdg6-1.xx.fbcdn.net/v/t39.30808-6/999999999_333_n.jpg?x=1"
    assert photo_identity(same_a) == photo_identity(same_b) == "556857573"
    assert _dedupe_photos([same_a, same_b, other]) == [same_a, other]


def test_base_url_collapses_permalinks_to_numeric_id() -> None:
    """« /p/{slug}-{id} », « /people/{name}/{id} » and « profile.php?id={id} » don't accept /photos_by — use the id root."""
    base = FacebookEnrichmentScraper._base_url
    assert base("https://www.facebook.com/p/Tasty-Korea-61580535121729/") == "https://www.facebook.com/61580535121729"
    assert base("https://www.facebook.com/profile.php?id=100063586360699") == "https://www.facebook.com/100063586360699"
    assert (
        base("https://www.facebook.com/people/Cr%C3%AAperie-Doc-krampouz/100063598419514/?sk=photos")
        == "https://www.facebook.com/100063598419514"
    )
    # Username and bare-id URLs already accept the sub-pages — leave them untouched.
    assert base("https://www.facebook.com/TacosMexicanosMaru/") == "https://www.facebook.com/TacosMexicanosMaru"
    assert base("https://www.facebook.com/100063586360699") == "https://www.facebook.com/100063586360699"


def test_clean_social_url_strips_tracking_params() -> None:
    """Instagram / TikTok tracking junk is removed from stored social links."""
    cleaned = _clean_social_url("https://www.instagram.com/food_truck_mexicano_tacos_maru?igsh=abc&utm_source=qr")
    assert cleaned == "https://www.instagram.com/food_truck_mexicano_tacos_maru"


def test_build_from_raw_produces_facebook_enrichment() -> None:
    """The raw page payload + reviews text become a « facebook » EnrichmentData."""
    dom = {
        "place_title": "Food truck mexicain Tacos Maru",
        "about_text": _ABOUT_TEXT,
        "intro_text": "",  # Intro card missing — fall back to embedded bio / og.
        "og_description": _OG_DESCRIPTION,
        "embedded_texts": _PAGE_EMBEDDED_BIO,
        "social": {
            "facebook": "https://www.facebook.com/TacosMexicanosMaru/",
            "instagram": "https://www.instagram.com/food_truck_mexicano_tacos_maru?igsh=abc",
            "tiktok": "https://www.tiktok.com/@food.truck.mexicai?_r=1&_t=ZN-93MqQbLcVJ0",
        },
        "website": None,
        "profile_photo": "https://scontent.xx.fbcdn.net/v/t1/logo.jpg",
    }
    gallery = [
        "https://static.xx.fbcdn.net/rsrc.php/icon.webp",
        "https://scontent.xx.fbcdn.net/v/t1/photo.jpg",
    ]
    data = FacebookEnrichmentScraper._build_from_raw(dom, "Fox only", gallery, _EMBEDDED_TEXTS)
    assert data.source == "facebook"
    assert data.rating == 4.8
    assert data.reviews_count == 22
    assert data.description is not None
    assert "saveurs mexicaines" in data.description
    assert "faite de manière artisanale" in data.description
    assert "Des..." not in data.description
    assert data.social_links["tiktok"].endswith("food.truck.mexicai")
    assert "igsh=" not in data.social_links["instagram"]
    assert data.website is None
    assert data.logo_url == "https://scontent.xx.fbcdn.net/v/t1/logo.jpg"
    assert data.photos == ["https://scontent.xx.fbcdn.net/v/t1/photo.jpg"]
    assert len(data.reviews) >= 3
    authors = {review["author"] for review in data.reviews}
    assert "Marie Breton" in authors
    assert "Guillaume Fournier" in authors
    # Disabled-comments chrome must never become a review body.
    assert all("commentaires ont été désactivés" not in review["text"].lower() for review in data.reviews)


def test_build_from_raw_does_not_duplicate_reviews_across_dom_and_relay() -> None:
    """Relay JSON and the visible DOM list the same people — keep each author once."""
    dom = {
        "place_title": "Food truck mexicain Tacos Maru",
        "about_text": _ABOUT_TEXT,
        "intro_text": _INTRO_TEXT,
        "og_description": _OG_DESCRIPTION,
        "embedded_texts": _PAGE_EMBEDDED_BIO,
        "social": {},
        "website": None,
        "profile_photo": None,
    }
    data = FacebookEnrichmentScraper._build_from_raw(dom, _REVIEWS_TEXT, None, _EMBEDDED_TEXTS)
    authors = [review["author"] for review in data.reviews]
    assert authors == list(dict.fromkeys(authors))
    assert authors.count("Fox Emmanuel") == 1
    fox = next(review for review in data.reviews if review["author"] == "Fox Emmanuel")
    # First-seen is the Relay body (no « Plats excellents » DOM chrome).
    assert "Copieux et délicieux" in fox["text"]
    assert "Plats excellents" not in fox["text"]


def test_build_from_raw_captures_page_harvested_email() -> None:
    """A contact email harvested from the page reaches EnrichmentData even when the main text has none.

    Regression: Garage Direct AUTO showed « direct-auto-21@outlook.fr » in a Coordonnées row rendered
    outside div[role="main"], so the about_text scan (main only) missed it. The page JS now harvests
    the email into dom["emails"], independent of where it renders.
    """
    dom = {
        "place_title": "Garage Direct AUTO",
        "about_text": "Garage Direct AUTO\nRecommandé par 100 % (12 avis)",
        "intro_text": "",
        "og_description": None,
        "embedded_texts": [],
        "social": {},
        "website": None,
        "profile_photo": None,
        "emails": ["direct-auto-21@outlook.fr"],
    }
    data = FacebookEnrichmentScraper._build_from_raw(dom, "", None, [])
    assert data.emails == ["direct-auto-21@outlook.fr"]


def test_build_from_raw_ranks_harvested_email_before_body_text() -> None:
    """The harvested contact email outranks one found in the page text — it becomes the send address."""
    dom = {
        "place_title": "Garage Direct AUTO",
        "about_text": "Ancien contact : vieux-contact@orange.fr",
        "intro_text": "",
        "og_description": None,
        "embedded_texts": [],
        "social": {},
        "website": None,
        "profile_photo": None,
        "emails": ["direct-auto-21@outlook.fr"],
    }
    data = FacebookEnrichmentScraper._build_from_raw(dom, "", None, [])
    assert data.emails[0] == "direct-auto-21@outlook.fr"
    assert "vieux-contact@orange.fr" in data.emails
