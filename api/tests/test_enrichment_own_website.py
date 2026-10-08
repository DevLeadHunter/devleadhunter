"""Only the business's own website counts: a network, directory or social page never makes a prospect « has a site »."""

from services.enrichment_service import EnrichmentService
from services.prospect_search.candidate_verifier import CandidateVerifier

_NETWORK_PAGE = "https://www.garage-exemple.myautoconseil.com/"


def test_a_garage_network_page_is_not_the_business_website() -> None:
    """A garage's page on its supplier's network is ignored: the garage stays a « no website » target."""
    assert not CandidateVerifier.is_own_website(_NETWORK_PAGE)
    assert EnrichmentService._own_website(None, listed=_NETWORK_PAGE) is None


def test_a_stored_page_that_is_not_its_site_gives_way_to_the_real_one() -> None:
    """A network or social page stored by an import is dropped; a real site on the listing takes its place."""
    replaced = EnrichmentService._own_website(_NETWORK_PAGE, listed="https://garage-exemple.fr")

    assert replaced == "https://garage-exemple.fr"
    assert EnrichmentService._own_website("https://www.facebook.com/garage.exemple", listed=None) is None


def test_a_real_stored_website_is_kept() -> None:
    """A real website already known wins over the one the listing shows."""
    kept = EnrichmentService._own_website("https://garage-exemple.fr", listed="https://autre-exemple.fr")

    assert kept == "https://garage-exemple.fr"
