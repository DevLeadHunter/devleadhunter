"""Professional license (RBQ) lookup: eligibility, strict name + city matching, registry failures, persistence."""

import json
from collections.abc import Callable
from types import SimpleNamespace

import httpx
import pytest

from enums.professional_license_source import ProfessionalLicenseSource
from services import professional_license_service as pls
from services.enrichment_service import EnrichmentService
from services.templates import site_content as sc

SEARCH_PAYLOAD = {
    "retour": {
        "licences": [
            {
                "nomIntervenant": "Plomberie Charbonneau inc.",
                "autresNoms": None,
                "noLicence": "1117453960",
                "statutLicence": 3,
                "typeLicence": 1,
                "adresseLigne2": "Montréal QC",
            },
            {
                "nomIntervenant": "Plomberie Cédric Charbonneau inc.",
                "autresNoms": None,
                "noLicence": "5799985601",
                "statutLicence": 3,
                "typeLicence": 1,
                "adresseLigne2": "Saint-Gabriel-de-Brandon QC",
            },
            {
                "nomIntervenant": "Charbonneau Richard",
                "autresNoms": "Plomberie Richard Charbonneau",
                "noLicence": "8213445336",
                "statutLicence": 1,
                "typeLicence": 1,
                "adresseLigne2": "Saint-Gabriel QC",
            },
        ]
    },
    "succes": True,
    "messages": [],
}


def _prospect(**overrides: object) -> SimpleNamespace:
    base = {
        "id": 42,
        "name": "Plomberie Charbonneau",
        "city": "Montréal",
        "country": "CA",
        "category": "Plombier",
        "user_id": 7,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _holder(**overrides: object) -> pls.RbqLicenseHolder:
    base = {
        "business_name": "Plomberie Charbonneau inc.",
        "other_names": "",
        "license_number": "1117453960",
        "city": "Montréal",
        "status_code": 3,
        "license_type_code": 1,
    }
    base.update(overrides)
    return pls.RbqLicenseHolder(**base)


def _route_registry_calls_to(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    """Make every httpx client of the service answer through ``handler`` instead of the network."""
    original_client = httpx.AsyncClient

    def client_with_mock_transport(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(pls.httpx, "AsyncClient", client_with_mock_transport)


class _FakeDb:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


class _StubRegistry:
    def __init__(self, holders: list[pls.RbqLicenseHolder] | None) -> None:
        self.holders = holders
        self.queries: list[str] = []

    async def search_by_business_name(self, business_name: str) -> list[pls.RbqLicenseHolder] | None:
        self.queries.append(business_name)
        return self.holders


def test_only_quebec_building_trades_are_eligible() -> None:
    """Québec plumbers, electricians and general contractors need an RBQ license; garages and French prospects do not."""
    assert pls.ProfessionalLicenseService.is_eligible(_prospect(category="Plombier")) is True
    assert pls.ProfessionalLicenseService.is_eligible(_prospect(category="Entrepreneur électricien")) is True
    assert pls.ProfessionalLicenseService.is_eligible(_prospect(category="Entrepreneur général")) is True
    assert pls.ProfessionalLicenseService.is_eligible(_prospect(category="Paysagiste")) is True
    assert pls.ProfessionalLicenseService.is_eligible(_prospect(category="Garage automobile")) is False
    assert pls.ProfessionalLicenseService.is_eligible(_prospect(category="Barbier")) is False
    assert pls.ProfessionalLicenseService.is_eligible(_prospect(category="Plombier", country="FR")) is False
    assert pls.ProfessionalLicenseService.is_eligible(_prospect(category="Plombier", country=None)) is False


def test_parse_search_results_reads_holders_and_strips_the_province() -> None:
    """Registry rows become holders; the municipality drops its « QC » suffix."""
    holders = pls.RbqLicenseRegistryClient.parse_search_results(SEARCH_PAYLOAD)

    assert [holder.license_number for holder in holders] == ["1117453960", "5799985601", "8213445336"]
    assert holders[0].city == "Montréal"
    assert holders[2].other_names == "Plomberie Richard Charbonneau"
    assert pls.RbqLicenseRegistryClient.parse_search_results({"retour": None}) == []


def test_pick_match_requires_name_and_city_to_agree() -> None:
    """The Montréal holder matches; the same-name holders elsewhere are homonyms and never win."""
    holders = pls.RbqLicenseRegistryClient.parse_search_results(SEARCH_PAYLOAD)

    match = pls.ProfessionalLicenseService.pick_match("Plomberie Charbonneau", "Montréal", holders)
    assert match is not None
    assert match.license_number == "1117453960"

    assert pls.ProfessionalLicenseService.pick_match("Plomberie Charbonneau", "Laval", holders) is None


def test_pick_match_rejects_ambiguous_same_city_candidates() -> None:
    """Two plausible holders in the prospect's city → nothing, unless exactly one name matches fully."""
    ambiguous = [
        _holder(business_name="Plomberie Charbonneau Nord inc.", license_number="1111111101"),
        _holder(business_name="Plomberie Charbonneau Sud inc.", license_number="2222222201"),
    ]
    assert pls.ProfessionalLicenseService.pick_match("Plomberie Charbonneau", "Montréal", ambiguous) is None

    with_exact = [*ambiguous, _holder(business_name="Plomberie Charbonneau inc.", license_number="3333333301")]
    match = pls.ProfessionalLicenseService.pick_match("Plomberie Charbonneau", "Montréal", with_exact)
    assert match is not None
    assert match.license_number == "3333333301"


def test_pick_match_filters_invalid_licenses_and_owner_builders() -> None:
    """A non-valid license or an owner-builder license is never attributed to a business."""
    assert (
        pls.ProfessionalLicenseService.pick_match("Plomberie Charbonneau", "Montréal", [_holder(status_code=1)]) is None
    )
    assert (
        pls.ProfessionalLicenseService.pick_match("Plomberie Charbonneau", "Montréal", [_holder(license_type_code=2)])
        is None
    )
    restricted = pls.ProfessionalLicenseService.pick_match(
        "Plomberie Charbonneau", "Montréal", [_holder(status_code=2)]
    )
    assert restricted is not None


def test_pick_match_uses_the_trade_name_and_tolerates_saint_abbreviations() -> None:
    """« Autres noms » (trade name) counts, and « St-Jérôme » equals « Saint-Jérôme »."""
    holder = _holder(business_name="9479-7495 Québec inc.", other_names="Électricité Lavoie", city="Saint-Jérôme")

    match = pls.ProfessionalLicenseService.pick_match("Electricité Lavoie", "St-Jérôme", [holder])
    assert match is holder
    assert pls.ProfessionalLicenseService.pick_match("Electricité Lavoie", None, [holder]) is None


def test_license_number_is_formatted_like_the_rbq() -> None:
    """10 digits → 4-4-2, 8 digits → 4-4, anything else untouched."""
    assert pls.ProfessionalLicenseService.format_license_number("1117453960") == "1117-4539-60"
    assert pls.ProfessionalLicenseService.format_license_number("1117-4539-60") == "1117-4539-60"
    assert pls.ProfessionalLicenseService.format_license_number("11174539") == "1117-4539"
    assert pls.ProfessionalLicenseService.format_license_number("ABC") == "ABC"


@pytest.mark.asyncio
async def test_registry_client_returns_none_when_the_registry_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 503 or a network error is reported as « unavailable » (None), never raised."""

    _route_registry_calls_to(monkeypatch, lambda request: httpx.Response(503, text="maintenance"))
    assert await pls.RbqLicenseRegistryClient().search_by_business_name("Plomberie Charbonneau") is None


@pytest.mark.asyncio
async def test_registry_client_posts_the_business_name_search(monkeypatch: pytest.MonkeyPatch) -> None:
    """The search uses the registry's « par entreprise » mode and parses the holders."""
    requests: list[httpx.Request] = []

    def answer_with_holders(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=SEARCH_PAYLOAD)

    _route_registry_calls_to(monkeypatch, answer_with_holders)
    holders = await pls.RbqLicenseRegistryClient().search_by_business_name("Plomberie Charbonneau")

    assert str(requests[0].url) == pls.RBQ_REGISTRY_SEARCH_URL
    sent_body = json.loads(requests[0].content)
    assert sent_body["ModeRecherche"] == 1
    assert sent_body["CriteresRecherche"] == {"NomEntreprise": "Plomberie Charbonneau"}
    assert holders is not None
    assert len(holders) == 3
    assert await pls.RbqLicenseRegistryClient().search_by_business_name("A") == []


@pytest.mark.asyncio
async def test_lookup_returns_a_formatted_match_with_its_provenance() -> None:
    """A concordant holder yields the RBQ label, the dashed number and a French provenance."""
    service = pls.ProfessionalLicenseService(registry_client=_StubRegistry([_holder()]))

    match = await service.lookup(_prospect())

    assert match is not None
    assert match.label == "Licence RBQ"
    assert match.number == "1117-4539-60"
    assert match.source == ProfessionalLicenseSource.RBQ_REGISTRY.value
    assert "Montréal" in match.provenance


@pytest.mark.asyncio
async def test_lookup_skips_ineligible_prospects_and_unavailable_registry() -> None:
    """A French prospect never hits the registry; an unavailable registry yields None."""
    registry = _StubRegistry([_holder()])
    service = pls.ProfessionalLicenseService(registry_client=registry)
    assert await service.lookup(_prospect(country="FR")) is None
    assert registry.queries == []

    assert await pls.ProfessionalLicenseService(registry_client=_StubRegistry(None)).lookup(_prospect()) is None


@pytest.mark.asyncio
async def test_resolve_for_enrichment_persists_the_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """A match lands on the record with the registry source; the outcome is logged as a diagnostic."""
    recorded: list[dict[str, object]] = []
    monkeypatch.setattr(pls.scraper_diagnostics_service, "record", lambda **kwargs: recorded.append(kwargs))
    service = pls.ProfessionalLicenseService(registry_client=_StubRegistry([_holder()]))
    record = SimpleNamespace(
        professional_license_label=None, professional_license_number=None, professional_license_source=None
    )
    db = _FakeDb()

    await service.resolve_for_enrichment(db, _prospect(), record)

    assert record.professional_license_label == "Licence RBQ"
    assert record.professional_license_number == "1117-4539-60"
    assert record.professional_license_source == ProfessionalLicenseSource.RBQ_REGISTRY.value
    assert db.commits == 1
    assert recorded[0]["source"] == pls.RBQ_DIAGNOSTIC_SOURCE
    assert recorded[0]["status"] == pls.STATUS_OK


@pytest.mark.asyncio
async def test_resolve_for_enrichment_never_overwrites_a_manual_license() -> None:
    """A number typed by a human wins — the registry is not even queried."""
    registry = _StubRegistry([_holder()])
    service = pls.ProfessionalLicenseService(registry_client=registry)
    record = SimpleNamespace(
        professional_license_label="Licence RBQ",
        professional_license_number="9999-9999-99",
        professional_license_source=ProfessionalLicenseSource.MANUAL.value,
    )

    await service.resolve_for_enrichment(_FakeDb(), _prospect(), record)

    assert record.professional_license_number == "9999-9999-99"
    assert registry.queries == []


@pytest.mark.asyncio
async def test_resolve_for_enrichment_swallows_registry_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """An exploding registry leaves the record untouched and is reported as an error diagnostic."""
    recorded: list[dict[str, object]] = []
    monkeypatch.setattr(pls.scraper_diagnostics_service, "record", lambda **kwargs: recorded.append(kwargs))

    class _ExplodingRegistry:
        async def search_by_business_name(self, business_name: str) -> list[pls.RbqLicenseHolder] | None:
            raise RuntimeError("boom")

    service = pls.ProfessionalLicenseService(registry_client=_ExplodingRegistry())
    record = SimpleNamespace(
        professional_license_label=None, professional_license_number=None, professional_license_source=None
    )
    db = _FakeDb()

    await service.resolve_for_enrichment(db, _prospect(), record)

    assert record.professional_license_number is None
    assert db.commits == 0
    assert recorded[0]["status"] == pls.STATUS_ERROR


def test_manual_license_edit_marks_the_source_as_manual() -> None:
    """Typing a license in the drawer flags it manual; clearing the number clears the source."""
    record = SimpleNamespace(
        professional_license_label=None,
        professional_license_number=None,
        professional_license_source=ProfessionalLicenseSource.RBQ_REGISTRY.value,
        status="completed",
    )

    class _Db(_FakeDb):
        def refresh(self, _record: object) -> None:
            return None

    EnrichmentService().update(
        _Db(), record, {"professional_license_label": "Licence RBQ", "professional_license_number": "5678-1234-01"}
    )
    assert record.professional_license_number == "5678-1234-01"
    assert record.professional_license_source == ProfessionalLicenseSource.MANUAL.value

    EnrichmentService().update(_Db(), record, {"professional_license_number": None})
    assert record.professional_license_source is None


def test_site_content_carries_the_license_only_with_a_number() -> None:
    """The enrichment license reaches the flat SiteContent; a label without a number is dropped."""
    site = sc.map_prospect_and_enrichment(
        business_name="Plomberie Charbonneau",
        phone=None,
        email=None,
        city="Montréal",
        area="Montréal",
        subtitle="",
        palette={},
        enrichment={"professional_license_label": "Licence RBQ", "professional_license_number": " 1117-4539-60 "},
    )
    assert site["professionalLicenseLabel"] == "Licence RBQ"
    assert site["professionalLicenseNumber"] == "1117-4539-60"

    without_number = sc.map_prospect_and_enrichment(
        business_name="Plomberie Charbonneau",
        phone=None,
        email=None,
        city="Montréal",
        area="Montréal",
        subtitle="",
        palette={},
        enrichment={"professional_license_label": "Licence RBQ", "professional_license_number": None},
    )
    assert without_number["professionalLicenseLabel"] == ""
    assert without_number["professionalLicenseNumber"] == ""


def test_license_round_trips_through_the_storyblok_contact_section() -> None:
    """The two license fields live in ``section_contact`` and flow back from a published story."""
    body = sc.to_storyblok_site_content(
        {"professionalLicenseLabel": "Licence RBQ", "professionalLicenseNumber": "1117-4539-60"}, ["contact"]
    )
    contact = next(blok for blok in body if blok["component"] == "section_contact")
    assert contact["professionalLicenseLabel"] == "Licence RBQ"
    assert contact["professionalLicenseNumber"] == "1117-4539-60"

    flat = sc.from_storyblok_site_content({"component": "page", "body": body})
    assert flat["professionalLicenseLabel"] == "Licence RBQ"
    assert flat["professionalLicenseNumber"] == "1117-4539-60"

    schema = next(component for component in sc.SITE_CONTENT_SCHEMAS if component["name"] == "section_contact")
    assert schema["schema"]["professionalLicenseNumber"]["type"] == "text"
    assert schema["schema"]["professionalLicenseLabel"]["pos"] < schema["schema"]["logo"]["pos"]


def test_landscaper_contact_override_keeps_the_license_fields() -> None:
    """The landscaper's per-section contact override exposes the license like the shared default."""
    from services.templates import landscaper_verdure

    assert "professionalLicenseNumber" in landscaper_verdure.SECTION_FIELDS["contact"]
    assert "professionalLicenseLabel" in landscaper_verdure.SECTION_FIELDS["contact"]


def test_a_license_reaches_only_the_site_of_a_country_whose_law_asks_for_one() -> None:
    """Québec (RBQ) and Luxembourg (autorisation d'établissement) show a license; any other country drops it."""
    site = {
        "businessName": "Toitures Gagnon",
        "professionalLicenseLabel": "Licence",
        "professionalLicenseNumber": "5678-1234-01",
    }

    for country in ("CA", "LU"):
        assert sc.apply_country_conventions(site, country)["professionalLicenseNumber"] == "5678-1234-01"
    for country in ("FR", "CH", "BE"):
        dropped = sc.apply_country_conventions(site, country)
        assert dropped["professionalLicenseLabel"] == ""
        assert dropped["professionalLicenseNumber"] == ""
    assert site["professionalLicenseNumber"] == "5678-1234-01"


def test_a_license_typed_for_a_french_prospect_never_reaches_its_built_site() -> None:
    """The country gate runs where every site is built, from the same enrichment."""
    from services.storyblok_service import StoryblokService

    def built_license_number(country: str) -> str:
        return StoryblokService().build_content_json(
            business_name="Toitures Gagnon",
            phone=None,
            email=None,
            city="Laval",
            description=None,
            template_id="artisan-edito",
            enrichment={"professional_license_label": "Licence RBQ", "professional_license_number": "5678-1234-01"},
            country=country,
        )["professionalLicenseNumber"]

    assert built_license_number("CA") == "5678-1234-01"
    assert built_license_number("FR") == ""


def test_the_cms_gets_the_license_fields_only_where_the_law_asks_for_a_license() -> None:
    """A French site's contact form has no license fields; a Québec or Luxembourg one keeps them, overrides included."""
    from services.templates import registry

    license_fields = {"professionalLicenseLabel", "professionalLicenseNumber"}
    for template_id in ("artisan-edito", "landscaper-verdure"):
        contact_by_country = {
            country: next(
                component["schema"]
                for component in registry.content_schemas(template_id, country)
                if component["name"] == "section_contact"
            )
            for country in ("FR", "CA", "LU")
        }
        assert license_fields.isdisjoint(contact_by_country["FR"])
        assert license_fields <= contact_by_country["CA"].keys()
        assert license_fields <= contact_by_country["LU"].keys()
