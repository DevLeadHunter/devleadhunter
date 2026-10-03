"""
Unit tests for the enrichment identity guard — the check that the scraped
Google Maps place really is the prospect's business, not a homonym's listing.
All offline: the guard and the raw-payload parser are exercised on fixtures.
"""

import json
from types import SimpleNamespace

from scrappers.enrichment_scraper import EnrichmentData, EnrichmentScraper
from services.enrichment_service import EnrichmentService
from services.validation_service import ValidationService

# ── Place identity check ─────────────────────────────────────────────────────


def test_matching_place_passes() -> None:
    """Same name, same département → the data is about the right business."""
    assert (
        ValidationService.place_identity_mismatch(
            prospect_name="Plomberie Vidal",
            prospect_city="Rennes",
            prospect_postal_code="35000",
            place_title="Plomberie Vidal",
            place_city="Rennes",
            place_postal_code="35000",
        )
        is None
    )


def test_wrong_business_name_is_rejected() -> None:
    """A place named after a completely different business is rejected."""
    reason = ValidationService.place_identity_mismatch(
        prospect_name="Plomberie Vidal",
        prospect_city="Rennes",
        prospect_postal_code="35000",
        place_title="Boulangerie Martin",
        place_city="Rennes",
        place_postal_code="35000",
    )
    assert reason is not None
    assert "ne correspond pas" in reason


def test_same_name_other_department_is_rejected() -> None:
    """The homonym case: right name, wrong département → someone else's data."""
    reason = ValidationService.place_identity_mismatch(
        prospect_name="Plomberie Vidal",
        prospect_city="Clermont-Ferrand",
        prospect_postal_code="63000",
        place_title="Plomberie Vidal",
        place_city="Lille",
        place_postal_code="59000",
    )
    assert reason is not None
    assert "département" in reason


def test_neighbouring_commune_same_department_passes() -> None:
    """An artisan listed one commune away (same département) is NOT a homonym."""
    assert (
        ValidationService.place_identity_mismatch(
            prospect_name="Plomberie Vidal",
            prospect_city="Rennes",
            prospect_postal_code="35000",
            place_title="Plomberie Vidal",
            place_city="Cesson-Sévigné",
            place_postal_code="35510",
        )
        is None
    )


def test_city_comparison_used_when_postal_codes_missing() -> None:
    """Without postal codes, a plainly different city still exposes the homonym."""
    reason = ValidationService.place_identity_mismatch(
        prospect_name="Plomberie Vidal",
        prospect_city="Clermont-Ferrand",
        prospect_postal_code=None,
        place_title="Plomberie Vidal",
        place_city="Lille",
        place_postal_code=None,
    )
    assert reason is not None
    assert "homonyme" in reason


def test_city_spelling_variants_are_not_a_mismatch() -> None:
    """« Clermont Ferrand » vs « Clermont-Ferrand » is the same city."""
    assert (
        ValidationService.place_identity_mismatch(
            prospect_name="Plomberie Vidal",
            prospect_city="Clermont-Ferrand",
            prospect_postal_code=None,
            place_title="Plomberie Vidal",
            place_city="Clermont Ferrand",
            place_postal_code=None,
        )
        is None
    )


def test_missing_place_identity_skips_the_check() -> None:
    """Payloads from older desktop sidecars carry no place identity → no rejection."""
    assert (
        ValidationService.place_identity_mismatch(
            prospect_name="Plomberie Vidal",
            prospect_city="Rennes",
            prospect_postal_code="35000",
            place_title=None,
            place_city=None,
            place_postal_code=None,
        )
        is None
    )


def test_service_parses_prospect_postal_code_from_address() -> None:
    """The guard reads the prospect's postal code out of its free-text address."""
    prospect = SimpleNamespace(
        name="Plomberie Vidal",
        address="12 rue des Forges, 63000 Clermont-Ferrand",
        city="Clermont-Ferrand",
        country="FR",
    )
    data = EnrichmentData(place_title="Plomberie Vidal", place_city="Lille", place_postal_code="59000")
    reason = EnrichmentService._place_mismatch(prospect, data)
    assert reason is not None
    assert "département" in reason


# ── Exact-anchor bypass (guard is a name-SEARCH safeguard only) ──────────────


def test_guard_skipped_when_anchored_on_maps_url() -> None:
    """A stored Maps place URL is an exact anchor → the name guard is skipped, even when the owner
    stuffed prices into the listing name (« L'Elégance Barber … Coupe Adulte 23€ »)."""
    prospect = SimpleNamespace(google_maps_url="https://www.google.com/maps/place/L'Elegance+Barber/@43.5,1.4,17z")
    data = EnrichmentData(source="google", place_title="L'Elégance Barber Avec ou Sans RDV Coupe Adulte 23€")
    assert EnrichmentService._anchored_on_exact_listing(prospect, data) is True


def test_guard_skipped_for_facebook_source() -> None:
    """Facebook data comes from the page pasted for this prospect → also an exact anchor."""
    prospect = SimpleNamespace(google_maps_url=None)
    data = EnrichmentData(source="facebook", place_title="Anything at all")
    assert EnrichmentService._anchored_on_exact_listing(prospect, data) is True


def test_guard_applies_without_an_exact_anchor() -> None:
    """No Maps URL and a name-search (google) source → the homonym guard still runs."""
    prospect = SimpleNamespace(google_maps_url=None)
    data = EnrichmentData(source="google", place_title="Boulangerie Martin")
    assert EnrichmentService._anchored_on_exact_listing(prospect, data) is False


def test_guard_applies_when_maps_url_is_blank() -> None:
    """An empty Maps URL is not an anchor — the guard must not be skipped."""
    prospect = SimpleNamespace(google_maps_url="")
    data = EnrichmentData(source="google", place_title="Whatever")
    assert EnrichmentService._anchored_on_exact_listing(prospect, data) is False


# ── Cross-source identity check (registry ↔ Maps place) ─────────────────────


def _record_with_place(place_postal_code: str | None) -> SimpleNamespace:
    return SimpleNamespace(place_postal_code=place_postal_code)


def _registry_candidate(siege_postal_code: str | None) -> SimpleNamespace:
    return SimpleNamespace(primary=True, raw={"siege_postal_code": siege_postal_code})


def test_identity_check_coherent_when_same_department() -> None:
    """Registry siège and Maps place in the same département → coherent."""
    status, detail = EnrichmentService._identity_check(_record_with_place("35510"), _registry_candidate("35000"))
    assert status == "coherent"
    assert detail is not None and "même zone" in detail


def test_identity_check_conflict_when_departments_differ() -> None:
    """Registry siège in another département than the place → probable homonym."""
    status, detail = EnrichmentService._identity_check(_record_with_place("63000"), _registry_candidate("59000"))
    assert status == "conflict"
    assert detail is not None and "homonyme" in detail


def test_identity_check_skipped_without_both_anchors() -> None:
    """Missing place or siège postal code → no verdict at all."""
    assert EnrichmentService._identity_check(_record_with_place(None), _registry_candidate("59000")) == (None, None)
    assert EnrichmentService._identity_check(_record_with_place("63000"), _registry_candidate(None)) == (None, None)
    assert EnrichmentService._identity_check(_record_with_place("63000"), None) == (None, None)


def test_identity_check_ignores_supporting_candidates() -> None:
    """Only registry-grade candidates carry a siège to compare."""
    supporting = SimpleNamespace(primary=False, raw={"siege_postal_code": "59000"})
    assert EnrichmentService._identity_check(_record_with_place("63000"), supporting) == (None, None)


# ── Maps place identity as geo fallback for the cascade ─────────────────────


def test_context_uses_place_identity_when_address_has_no_postal_code() -> None:
    """A prospect without usable address borrows the validated place geo."""
    from services.decision_maker.resolver import context_from_prospect

    prospect = SimpleNamespace(
        name="Plomberie Vidal",
        address=None,
        city=None,
        website=None,
        website_status=None,
        phone=None,
    )
    enrichment = SimpleNamespace(
        description=None,
        reviews=[],
        place_postal_code="63000",
        place_city="Clermont-Ferrand",
    )
    context = context_from_prospect(prospect, enrichment)
    assert context.postal_code == "63000"
    assert context.city == "Clermont-Ferrand"


def test_context_prefers_the_prospect_own_address() -> None:
    """The prospect's own postal code always wins over the place fallback."""
    from services.decision_maker.resolver import context_from_prospect

    prospect = SimpleNamespace(
        name="Plomberie Vidal",
        address="12 rue des Forges, 35000 Rennes",
        city="Rennes",
        website=None,
        website_status=None,
        phone=None,
    )
    enrichment = SimpleNamespace(
        description=None,
        reviews=[],
        place_postal_code="63000",
        place_city="Clermont-Ferrand",
    )
    context = context_from_prospect(prospect, enrichment)
    assert context.postal_code == "35000"
    assert context.city == "Rennes"


def test_context_drops_dead_and_placeholder_websites() -> None:
    """Legal mentions of a dead site or a directory mini-site name the wrong person."""
    from services.decision_maker.resolver import context_from_prospect

    def prospect_with_status(website_status: str | None) -> SimpleNamespace:
        return SimpleNamespace(
            name="Plomberie Vidal",
            address=None,
            city="Rennes",
            website="https://plomberie-vidal.business.site",
            website_status=website_status,
            phone=None,
        )

    assert context_from_prospect(prospect_with_status("dead")).website is None
    assert context_from_prospect(prospect_with_status("placeholder")).website is None
    assert context_from_prospect(prospect_with_status("live")).website is not None
    assert context_from_prospect(prospect_with_status(None)).website is not None


# ── Raw-payload parsing (place identity extraction) ──────────────────────────


def test_build_from_raw_extracts_place_identity() -> None:
    """The h1 title and the JSON-LD address feed the identity fields."""
    ld_block = json.dumps(
        {
            "@type": "Plumber",
            "name": "Plomberie Vidal",
            "telephone": "+33 3 20 00 00 00",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "4 rue de la Clef",
                "postalCode": "59000",
                "addressLocality": "Lille",
            },
        }
    )
    data = EnrichmentScraper._build_from_raw(
        {"place_title": "Plomberie Vidal", "ld": [ld_block]},
        business_name="Plomberie Vidal",
        city="Lille",
    )
    assert data.place_title == "Plomberie Vidal"
    assert data.place_city == "Lille"
    assert data.place_postal_code == "59000"


def test_build_from_raw_without_identity_stays_none() -> None:
    """No h1 and no JSON-LD → identity fields stay None (check skipped later)."""
    data = EnrichmentScraper._build_from_raw({}, business_name="Plomberie Vidal", city="Lille")
    assert data.place_title is None
    assert data.place_city is None
    assert data.place_postal_code is None


def test_build_from_raw_drops_section_header_title() -> None:
    """An h1 read while the « Horaires » sub-panel is open must not become the place title:
    it falls back to the JSON-LD business name instead of poisoning the homonym guard."""
    ld_block = json.dumps(
        {
            "@type": "Restaurant",
            "name": "Hell's Cantina",
            "address": {"@type": "PostalAddress", "postalCode": "31840", "addressLocality": "Seilh"},
        }
    )
    data = EnrichmentScraper._build_from_raw(
        {"place_title": "Horaires", "ld": [ld_block]},
        business_name="Hell's Cantina",
        city="Seilh",
    )
    assert data.place_title == "Hell's Cantina"


def test_build_from_raw_section_header_without_ld_stays_none() -> None:
    """A section-header h1 with no JSON-LD name → title dropped, so the guard skips (never rejects)."""
    data = EnrichmentScraper._build_from_raw(
        {"place_title": "Horaires"},
        business_name="Hell's Cantina",
        city="Seilh",
    )
    assert data.place_title is None


def test_clean_place_title_drops_maps_section_headers() -> None:
    """The cleaner strips Google Maps section headers (any case) but keeps a real business name."""
    from scrappers.enrichment_scraper import _clean_place_title

    assert _clean_place_title("Horaires") is None
    assert _clean_place_title("  AVIS ") is None
    assert _clean_place_title("Photos") is None
    assert _clean_place_title("Hell's Cantina") == "Hell's Cantina"
    assert _clean_place_title(None) is None
    assert _clean_place_title("") is None
