"""
Round 19 of the search training (search n° 20, Swiss garages): a directory's own email read on its page about the
business, an email naming a firm the register seats in another town, and the Google photos of a listing whose 360°
shots never load. Each case is a real one, its names, numbers and people replaced.
"""

import asyncio
import io
import random
import re
from typing import Any

import httpx
import pytest
from PIL import Image

from enums.prospect_search import CandidateOrigin, CandidateStatus, EmailProofLevel, ProspectSearchChannel
from scrappers.enrichment_scraper import _EXTRACT_JS, _GRID_PHOTOS_JS, GalleryCuration
from services.decision_maker.normalize import fold
from services.prospect_search.candidate_decision import CandidateDecision, SearchCriteria
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.search_judge import SearchResultLine
from services.prospect_search.swiss_registry import SwissRegisterFirm, swiss_registry
from services.prospect_search.trade_catalog import TradeCatalog

_GARAGE = TradeCatalog.resolve("garage")
_EMAIL_ONLY = SearchCriteria(channel=ProspectSearchChannel.EMAIL, only_without_website=True, minimum_rating=4.0)
_REAL_ASYNC_CLIENT = httpx.AsyncClient
_PHOTO_SPHERE_THUMBNAIL = (
    "https://lh3.googleusercontent.com/gps-cs-s/EXEMPLE0photo0sphere=w203-h100-k-no-pi-20-ya174.09999-ro-0-fo100"
)


def _garage(name: str, town: str, **overrides: object) -> CandidateFacts:
    """A Swiss garage's Google listing, verified on Google."""
    values: dict[str, object] = {
        "name": name,
        "trade_key": "garage",
        "country": "CH",
        "origin": CandidateOrigin.GOOGLE_LOCAL.value,
        "city": town,
        "searched_city": town,
        "address": f"Rue de l'Exemple 1, 1999 {town}",
        "phone": "079 000 00 01",
        "google_rating": 4.9,
        "google_reviews_count": 90,
        "is_verified": True,
    }
    values.update(overrides)
    return CandidateFacts(**values)  # type: ignore[arg-type]


def _directory_page(host: str) -> SearchResultLine:
    """A garage directory's page about the business, its own contact in the footer."""
    return SearchResultLine(
        link=f"https://www.{host}/",
        host=host,
        title="Garage Exemple Motors – Used Car Dealer in Exempleville",
        description=f"Garage Exemple Motors - Exempleville, Switzerland. Garage Categories ... Email us: info@{host}.",
    )


def test_a_directory_s_own_email_on_its_page_about_the_business_is_never_the_business_s() -> None:
    """« Email us: info@trouve-garage.ch » in the footer of a garage directory's page about the business."""
    facts = _garage("Garage Exemple Motors", "Exempleville")

    CandidateVerifier.offer_email_read_in(
        facts,
        "info@trouve-garage.ch",
        EmailProofLevel.DIRECTORY,
        _directory_page("trouve-garage.ch"),
        _GARAGE,
        department=None,
        is_own_text=False,
    )

    assert facts.email is None


@pytest.mark.parametrize(
    ("email", "host", "website", "is_publisher"),
    [
        ("info@trouve-garage.ch", "trouve-garage.ch", None, True),
        ("contact@trouve-garage.ch", "fr.trouve-garage.ch", None, True),
        ("garage.exemple.motors@gmail.com", "trouve-garage.ch", None, False),
        ("contact@garage-exemple-motors.ch", "garage-exemple-motors.ch", None, False),
        ("contact@gem-auto.ch", "gem-auto.ch", "https://www.gem-auto.ch/", False),
    ],
)
def test_only_a_site_that_is_not_the_business_s_publishes_its_own_address(
    email: str, host: str, website: str | None, is_publisher: bool
) -> None:
    facts = _garage("Garage Exemple Motors", "Exempleville", website=website)

    assert CandidateVerifier.is_publisher_address(email, _directory_page(host), facts, _GARAGE) is is_publisher


def _register(monkeypatch: pytest.MonkeyPatch, firms: list[SwissRegisterFirm]) -> list[str]:
    """The register finds a firm by the start of one of its words; the queries are kept."""
    queries: list[str] = []

    async def firms_named(query: str, *, max_entries: int = 10) -> list[SwissRegisterFirm]:
        queries.append(query)
        wanted = fold(query)
        return [firm for firm in firms if any(word.startswith(wanted) for word in fold(firm.name).split())]

    monkeypatch.setattr(swiss_registry, "firms_named", firms_named)
    return queries


def _firm(name: str, seat: str) -> SwissRegisterFirm:
    return SwissRegisterFirm(name=name, seat=seat, status="EXISTIEREND", uid="CHE-000.000.001")


def test_an_email_naming_a_firm_the_register_seats_in_another_town_is_left_to_confirm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """« garagetemoin@ » for a Garage de la Gare: the register knows the Temoin one eighty kilometres away."""
    _register(monkeypatch, [_firm("Garage de la Gare Jules Temoin S.A.", "Autreville")])
    facts = _garage("Garage de la Gare", "Exempleville", email="garagetemoin@gmail.com", email_proof_level="a")

    asyncio.run(swiss_registry.note_email_firm_elsewhere(facts))
    verdict = CandidateDecision.decide(facts, _GARAGE, _EMAIL_ONLY)

    assert (verdict.status, verdict.detail) == (
        CandidateStatus.TO_CONFIRM,
        "Son email (garagetemoin@gmail.com) désigne un autre endroit (Autreville, où le registre inscrit « Garage de "
        "la Gare Jules Temoin S.A. ») que Exempleville : à vérifier, ce peut être un homonyme.",
    )


@pytest.mark.parametrize(
    "firms",
    [
        [_firm("Garage de la Gare Jules Temoin S.A.", "Autreville"), _firm("Temoin Garage", "Exempleville")],
        [_firm("Temoin Immobilier SA", "Autreville")],
        [],
    ],
)
def test_an_email_naming_a_firm_here_or_of_another_trade_says_nothing(
    monkeypatch: pytest.MonkeyPatch, firms: list[SwissRegisterFirm]
) -> None:
    _register(monkeypatch, firms)
    facts = _garage("Garage de la Gare", "Exempleville", email="garagetemoin@gmail.com", email_proof_level="a")

    asyncio.run(swiss_registry.note_email_firm_elsewhere(facts))

    assert facts.contact_elsewhere is None


def test_a_first_name_in_the_email_is_never_searched_in_the_register(monkeypatch: pytest.MonkeyPatch) -> None:
    queries = _register(monkeypatch, [_firm("Garage de la Gare Thomas SA", "Autreville")])
    facts = _garage("Garage de la Gare", "Exempleville", email="garage.thomas@gmail.com", email_proof_level="a")

    asyncio.run(swiss_registry.note_email_firm_elsewhere(facts))

    assert (queries, facts.contact_elsewhere) == ([], None)


@pytest.mark.parametrize("script", [_EXTRACT_JS, _GRID_PHOTOS_JS])
def test_a_360_photo_s_size_block_is_replaced_whole_by_the_large_size(script: str) -> None:
    """A size block with decimals kept before « =s1600 » made two blocks, which Google answers with a 400."""
    size_block = re.search(r"/(=\[[^\]]+\]\+\$)/", script)

    assert size_block is not None
    assert re.sub(size_block.group(1), "=s1600", _PHOTO_SPHERE_THUMBNAIL) == (
        "https://lh3.googleusercontent.com/gps-cs-s/EXEMPLE0photo0sphere=s1600"
    )


def _jpeg(seed: int) -> bytes:
    generator = random.Random(seed)
    small = Image.new("RGB", (48, 36))
    small.putdata(
        [(generator.randrange(256), generator.randrange(256), generator.randrange(256)) for _ in range(48 * 36)]
    )
    buffer = io.BytesIO()
    small.resize((1200, 900), Image.Resampling.BICUBIC).save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def _google_answering(answers: dict[str, httpx.Response]) -> Any:
    """Build the HTTP clients the curation opens: each address answers as scripted."""

    def handler(request: httpx.Request) -> httpx.Response:
        return answers[str(request.url)]

    def build(**kwargs: Any) -> httpx.AsyncClient:
        return _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler), **kwargs)

    return build


def test_a_photo_address_google_answers_400_is_left_out_and_a_failing_one_is_kept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two shots of seven never loaded on the site; a photo the server could not serve now may load later."""
    photo = "https://lh3.googleusercontent.com/gps-cs-s/EXEMPLE1=s1600"
    broken = f"{_PHOTO_SPHERE_THUMBNAIL}=s1600"
    busy = "https://lh3.googleusercontent.com/gps-cs-s/EXEMPLE2=s1600"
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        _google_answering(
            {
                photo: httpx.Response(200, content=_jpeg(1), headers={"content-type": "image/jpeg"}),
                broken: httpx.Response(400, text="<html>Bad Request</html>", headers={"content-type": "text/html"}),
                busy: httpx.Response(503, text="busy"),
            }
        ),
    )

    gallery = asyncio.run(GalleryCuration.curate_gallery([photo, broken, busy]))

    assert gallery.photos == [photo, busy]


def test_a_logo_address_answering_404_is_no_logo(monkeypatch: pytest.MonkeyPatch) -> None:
    logo = "https://lh3.googleusercontent.com/EXEMPLE-logo=s1600"
    monkeypatch.setattr(httpx, "AsyncClient", _google_answering({logo: httpx.Response(404, text="Not found")}))

    assert asyncio.run(GalleryCuration.curate_gallery([], logo_url=logo)).logo_url is None
