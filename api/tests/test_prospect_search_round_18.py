"""
Round 18 of the search training (search n° 20, Swiss garages): Facebook's picture for a page without one taken as a
logo, a sole proprietorship naming its owner before its trade name, and a firm in liquidation whose name holds the
business's with its owner's added. Each case is a real one, its names, numbers and people replaced.
"""

import asyncio
import base64
import io
import random
from typing import Any

import pytest
from PIL import Image, ImageDraw

from enums.prospect_search import CandidateOrigin, CandidateStatus, ProspectSearchChannel
from scrappers.enrichment_scraper import GalleryCuration
from services.decision_maker.normalize import fold
from services.decision_maker.swiss_register_people import RegisteredPerson, SwissRegisterPeople
from services.prospect_search.candidate_decision import CandidateDecision, SearchCriteria
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.swiss_registry import SwissRegisterFirm, SwissRegistry, swiss_registry
from services.prospect_search.trade_catalog import TradeCatalog

_GARAGE = TradeCatalog.resolve("garage")
_EMAIL_ONLY = SearchCriteria(channel=ProspectSearchChannel.EMAIL, only_without_website=True, minimum_rating=4.0)
_AVATAR_SIDE = 600


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _data_uri(image: Image.Image) -> str:
    return "data:image/png;base64," + base64.b64encode(_png(image)).decode("ascii")


def _initial_avatar() -> Image.Image:
    """Facebook's picture for a page without one: its initial, dark blue on a flat light blue square."""
    image = Image.new("RGB", (_AVATAR_SIDE, _AVATAR_SIDE), (200, 222, 245))
    ImageDraw.Draw(image).arc([150, 150, 450, 450], start=40, end=320, fill=(40, 70, 140), width=70)
    return image


def _accented_initial_avatar() -> Image.Image:
    """The same picture for a page whose name opens on « É »: the letter and its accent, two shapes."""
    image = Image.new("RGB", (_AVATAR_SIDE, _AVATAR_SIDE), (240, 140, 60))
    draw = ImageDraw.Draw(image)
    for box in ([200, 200, 260, 470], [200, 200, 400, 250], [200, 310, 370, 360], [200, 420, 400, 470]):
        draw.rectangle(box, fill="white")
    draw.polygon([(280, 160), (340, 110), (360, 130), (300, 175)], fill="white")
    return image


def _silhouette_avatar() -> Image.Image:
    """Facebook's grey picture of a profile without one: a white bust on a flat grey square."""
    image = Image.new("RGB", (_AVATAR_SIDE, _AVATAR_SIDE), (211, 214, 219))
    draw = ImageDraw.Draw(image)
    draw.ellipse([190, 80, 410, 330], fill="white")
    draw.rounded_rectangle([60, 330, 540, 640], radius=150, fill="white")
    draw.rectangle([250, 300, 350, 360], fill="white")
    return image


def _monogram_on_white() -> Image.Image:
    """A business's own logo: one dark letter on white."""
    image = Image.new("RGB", (_AVATAR_SIDE, _AVATAR_SIDE), "white")
    ImageDraw.Draw(image).arc([150, 150, 450, 450], start=40, end=320, fill=(40, 70, 140), width=70)
    return image


def _name_on_colour() -> Image.Image:
    """A business's own logo: its name, five letters in white on a blue square."""
    image = Image.new("RGB", (_AVATAR_SIDE, _AVATAR_SIDE), (40, 70, 140))
    draw = ImageDraw.Draw(image)
    for left in range(70, 520, 95):
        draw.rectangle([left, 250, left + 60, 350], fill="white")
    return image


def _photo(seed: int) -> Image.Image:
    generator = random.Random(seed)
    small = Image.new("RGB", (48, 36))
    small.putdata(
        [(generator.randrange(256), generator.randrange(256), generator.randrange(256)) for _ in range(48 * 36)]
    )
    return small.resize((1200, 900), Image.Resampling.BICUBIC)


@pytest.mark.parametrize("avatar", [_initial_avatar, _accented_initial_avatar, _silhouette_avatar])
def test_facebook_s_picture_for_a_page_without_one_is_a_placeholder(avatar: Any) -> None:
    traits = GalleryCuration.traits_of(_png(avatar()))

    assert traits is not None and traits.is_placeholder_avatar
    assert GalleryCuration.unfit_reason(traits) == "placeholder avatar"


@pytest.mark.parametrize("logo", [_monogram_on_white, _name_on_colour])
def test_a_business_s_own_logo_is_no_placeholder(logo: Any) -> None:
    traits = GalleryCuration.traits_of(_png(logo()))

    assert traits is not None and not traits.is_placeholder_avatar


def test_the_placeholder_given_as_logo_is_no_logo() -> None:
    """A page without picture: Facebook's initial reached the site as its logo."""
    photo = _data_uri(_photo(1))

    gallery = asyncio.run(GalleryCuration.curate_gallery([photo], logo_url=_data_uri(_initial_avatar())))

    assert (gallery.photos, gallery.logo_url) == ([photo], None)


def test_the_placeholder_in_a_gallery_is_no_photo_and_never_becomes_the_logo() -> None:
    photo = _data_uri(_photo(2))

    gallery = asyncio.run(GalleryCuration.curate_gallery([_data_uri(_silhouette_avatar()), photo]))

    assert (gallery.photos, gallery.logo_url) == ([photo], None)


def test_a_sole_proprietorship_naming_its_owner_first_names_its_contact() -> None:
    """« Jean-Paul Modèle, Garage du Lac »: the owner opens the firm's name, before its trade name."""
    assert SwissRegisterPeople.owner_in_firm_name("Jean-Paul Modèle, Garage du Lac") == RegisteredPerson(
        first_name="Jean-Paul", last_name="Modèle", roles=("titulaire",), is_name_certain=True
    )


@pytest.mark.parametrize(
    ("firm_name", "owner"),
    [
        ("Garage des Deux Cantons, Modèle Jules", ("Jules", "Modèle")),
        ("Garage du Lac, Exemple", None),
        ("Garage du Lac, Carrosserie Exemple", None),
    ],
)
def test_the_owner_closing_the_firm_name_is_read_as_before(firm_name: str, owner: tuple[str, str] | None) -> None:
    person = SwissRegisterPeople.owner_in_firm_name(firm_name)

    assert ((person.first_name, person.last_name) if person else None) == owner


@pytest.mark.parametrize(
    ("firm_name", "is_named"),
    [
        ("Jean-Paul Modèle, Garage du Lac", True),
        ("Garage du Lac, Modèle", True),
        ("Garage du Lac Sàrl", True),
        ("Garage du Lac Modèle SA", False),
        ("Carrosserie du Lac, Modèle", False),
    ],
)
def test_a_firm_bears_the_business_s_name_beside_its_owner_s(firm_name: str, is_named: bool) -> None:
    assert SwissRegistry.is_named_like(firm_name, "Garage du Lac") is is_named


def _firm(name: str, seat: str, status: str = "EXISTIEREND", uid: str = "CHE-000.000.001") -> SwissRegisterFirm:
    return SwissRegisterFirm(name=name, seat=seat, status=status, uid=uid, register_id=1, legal_form_id=1)


def _register(
    monkeypatch: pytest.MonkeyPatch, firms: list[SwissRegisterFirm], addresses: dict[str, tuple[str, str]]
) -> None:
    """
    The register finds a firm by the start of its name, or of one of its words for a single word, and by any part
    of it after a « * »; each firm's registered address is scripted by its number.
    """

    async def firms_named(query: str, *, max_entries: int = 10) -> list[SwissRegisterFirm]:
        wanted = fold(query.lstrip("*"))
        return [
            firm
            for firm in firms
            if (wanted in fold(firm.name) if query.startswith("*") else fold(firm.name).startswith(wanted))
            or (" " not in wanted and any(word.startswith(wanted) for word in fold(firm.name).split()))
        ][:max_entries]

    async def detail(firm: SwissRegisterFirm) -> dict[str, Any]:
        postal_code, town = addresses.get(firm.uid, ("", ""))
        return {"address": {"swissZipCode": postal_code, "town": town}} if postal_code else {}

    monkeypatch.setattr(swiss_registry, "firms_named", firms_named)
    monkeypatch.setattr(swiss_registry, "_detail", detail)


def test_the_firm_naming_its_owner_first_is_found_at_the_business_s_seat(monkeypatch: pytest.MonkeyPatch) -> None:
    """The only active « Garage du Lac » sits elsewhere: the one of Exempleville names its owner first."""
    owner_first = _firm("Jean-Paul Modèle, Garage du Lac", "Exempleville", uid="CHE-000.000.002")
    _register(monkeypatch, [_firm("Garage du Lac Sàrl", "Modèle-sur-Lac"), owner_first], {})

    firm = asyncio.run(
        swiss_registry.firm_of(name="Garage du Lac", town="Exempleville", postal_code="2999", allow_unique_name=True)
    )

    assert firm == owner_first


def _garage_of_exempleville() -> CandidateFacts:
    """A garage's Google listing at Exempleville, with its email."""
    return CandidateFacts(
        name="CENTRE AUTO EXEMPLE",
        trade_key="garage",
        country="CH",
        origin=CandidateOrigin.GOOGLE_LOCAL.value,
        city="Exempleville",
        searched_city="Exempleville",
        address="Pré de l'Exemple 1, 1999 Exempleville",
        phone="076 000 00 01",
        email="centreautoexemple@exemple.ch",
        email_proof_level="b",
        google_rating=4.3,
        google_reviews_count=50,
        is_verified=True,
    )


_IN_LIQUIDATION = _firm("CENTRE AUTO EXEMPLE MODELE", "Exempleville", status="IN_AUFLOESUNG", uid="CHE-000.000.003")


def test_a_firm_in_liquidation_holding_the_name_with_a_new_firm_at_its_place_is_left_to_confirm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The owner's sole proprietorship went bankrupt; « EXEMPLE SWISS SA » was founded next door the same month."""
    successor = _firm("EXEMPLE SWISS SA", "Exempleville", uid="CHE-000.000.004")
    _register(monkeypatch, [_IN_LIQUIDATION, successor], {successor.uid: ("1999", "Exempleville")})
    facts = _garage_of_exempleville()

    asyncio.run(swiss_registry.read_closing(facts))
    verdict = CandidateDecision.decide(facts, _GARAGE, _EMAIL_ONLY)

    assert not facts.is_closed
    assert (verdict.status, verdict.detail) == (
        CandidateStatus.TO_CONFIRM,
        "Le registre du commerce donne « CENTRE AUTO EXEMPLE MODELE, en liquidation », et « EXEMPLE SWISS SA » est "
        "inscrite à Exempleville : à vérifier, l'atelier continue peut-être sous ce nom.",
    )


def test_a_firm_in_liquidation_holding_the_name_alone_closes_the_business(monkeypatch: pytest.MonkeyPatch) -> None:
    _register(monkeypatch, [_IN_LIQUIDATION], {})
    facts = _garage_of_exempleville()

    asyncio.run(swiss_registry.read_closing(facts))

    assert facts.is_closed
    assert CandidateDecision.decide(facts, _GARAGE, _EMAIL_ONLY).status == CandidateStatus.REJECTED


@pytest.mark.parametrize(
    "closed_firm",
    [
        _firm("CENTRE AUTO EXEMPLE MODELE", "Autreville", status="IN_AUFLOESUNG"),
        _firm("AUTO EXEMPLE MODELE", "Exempleville", status="IN_AUFLOESUNG"),
    ],
)
def test_a_closed_firm_elsewhere_or_short_of_the_name_closes_nothing(
    monkeypatch: pytest.MonkeyPatch, closed_firm: SwissRegisterFirm
) -> None:
    _register(monkeypatch, [closed_firm], {})
    facts = _garage_of_exempleville()

    asyncio.run(swiss_registry.read_closing(facts))

    assert not facts.is_closed
    assert facts.register_successor is None
