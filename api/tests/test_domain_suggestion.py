"""Domain suggestion + availability: a logical, ideally-free .fr pre-fill for a prospect.

Covers the credential-free core: the business name drives the logical candidates (code logic
ranks first), Groq only enriches valid extras, and RDAP availability decides the pre-fill —
never claiming a domain is free without a 404 from the registry.
"""

import asyncio
from typing import ClassVar

import pytest

import services.domain.availability as availability_module
from services.domain import suggestion_service as suggestion_module
from services.domain.availability import is_available
from services.domain.ovh_catalog import extract_create_price
from services.domain.suggestion_service import DomainCandidate, domain_suggestion_service


class _FakeResponse:
    def __init__(self, status_code: int, url: str) -> None:
        self.status_code = status_code
        self.url = url


class _FakeClient:
    """httpx.AsyncClient stand-in: yields a canned status, or raises a canned error, and records the URL asked."""

    requested: ClassVar[list[str]] = []

    def __init__(self, *, status: int | None, exc: Exception | None, redirect_to: str | None) -> None:
        self._status = status
        self._exc = exc
        self._redirect_to = redirect_to

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def get(self, url: str) -> _FakeResponse:
        _FakeClient.requested.append(url)
        if self._exc is not None:
            raise self._exc
        assert self._status is not None
        # Like httpx with ``follow_redirects``: the response URL is the final one, the request URL otherwise.
        return _FakeResponse(self._status, self._redirect_to or url)


def _patch_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    status: int | None = None,
    exc: Exception | None = None,
    redirect_to: str | None = None,
) -> None:
    _FakeClient.requested = []
    monkeypatch.setattr(
        availability_module.httpx,
        "AsyncClient",
        lambda **_kw: _FakeClient(status=status, exc=exc, redirect_to=redirect_to),
    )


class TestCandidateLabels:
    def test_builds_logical_variants_in_order(self) -> None:
        labels = domain_suggestion_service._candidate_labels("Chez Mimon", "Poitiers", "restaurant")
        assert labels == [
            "chezmimon",
            "chez-mimon",
            "chezmimon-poitiers",
            "chez-mimon-poitiers",
            "chezmimon-restaurant",
        ]

    def test_strips_accents_and_symbols(self) -> None:
        labels = domain_suggestion_service._candidate_labels("Café Créa+", None, None)
        assert labels == ["cafecrea", "cafe-crea"]

    def test_a_single_word_yields_one_label(self) -> None:
        # Compact and hyphenated collapse to the same string → deduped to one.
        assert domain_suggestion_service._candidate_labels("Tacosmaru", None, None) == ["tacosmaru"]


class TestAvailability:
    def test_404_means_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(monkeypatch, status=404)
        assert asyncio.run(is_available("tacos-maru.fr")) is True

    def test_200_means_taken(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(monkeypatch, status=200)
        assert asyncio.run(is_available("google.fr")) is False

    def test_a_com_is_checked_too(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(monkeypatch, status=200)
        assert asyncio.run(is_available("google.com")) is False

    def test_unexpected_status_is_inconclusive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_client(monkeypatch, status=500)
        assert asyncio.run(is_available("whatever.fr")) is None

    def test_network_error_is_inconclusive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        _patch_client(monkeypatch, exc=httpx.ConnectError("boom"))
        assert asyncio.run(is_available("whatever.fr")) is None

    def test_no_dot_is_not_checked(self) -> None:
        assert asyncio.run(is_available("example")) is None

    def test_each_registry_is_asked_on_its_own_server(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """.fr, .ch and .ca have an authoritative RDAP server; a 404 from it means available."""
        expected = {
            "tacos-maru.fr": "https://rdap.nic.fr/domain/tacos-maru.fr",
            "tacos-maru.ch": "https://rdap.nic.ch/domain/tacos-maru.ch",
            "tacos-maru.ca": "https://rdap.ca.fury.ca/rdap/domain/tacos-maru.ca",
        }
        for domain, url in expected.items():
            _patch_client(monkeypatch, status=404)
            assert asyncio.run(is_available(domain)) is True
            assert _FakeClient.requested == [url]
            _patch_client(monkeypatch, status=200)
            assert asyncio.run(is_available(domain)) is False

    def test_a_tld_without_registry_server_is_not_verifiable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """rdap.org answers 404 for .be and .lu (absent from the IANA bootstrap): never « available »."""
        for domain in ("tacos-maru.be", "tacos-maru.lu"):
            _patch_client(monkeypatch, status=404)
            assert asyncio.run(is_available(domain)) is None
            assert _FakeClient.requested == [f"https://rdap.org/domain/{domain}"]

    def test_a_bootstrap_redirect_to_the_registry_is_trusted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A .com goes through rdap.org, which forwards to Verisign: its 404 is a real « not registered »."""
        _patch_client(monkeypatch, status=404, redirect_to="https://rdap.verisign.com/com/v1/domain/tacos-maru.com")
        assert asyncio.run(is_available("tacos-maru.com")) is True


class TestOvhCatalogPrice:
    def test_extracts_the_fr_first_year_price(self) -> None:
        catalog = {
            "plans": [
                {
                    "planCode": "com",
                    "pricings": [{"mode": "create-default", "capacities": ["installation"], "price": 900000000}],
                },
                {
                    "planCode": "fr",
                    "pricings": [
                        {"mode": "create-default", "capacities": ["installation", "renew"], "price": 499000000},
                        {"mode": "create-default", "capacities": ["renew"], "price": 779000000},
                    ],
                },
            ]
        }
        assert extract_create_price(catalog, "fr") == pytest.approx(4.99)
        assert extract_create_price(catalog, "com") == pytest.approx(9.0)  # per-TLD, not always .fr

    def test_returns_none_when_tld_absent(self) -> None:
        assert extract_create_price({"plans": [{"planCode": "com", "pricings": []}]}, "fr") is None


class TestSuggest:
    @staticmethod
    def _run_suggest(
        monkeypatch: pytest.MonkeyPatch,
        *,
        availability: dict[str, bool | None],
        ai: list[str],
        country: str = "FR",
        priced_tlds: list[str] | None = None,
    ):
        async def _fake_map(domains: list[str]) -> dict[str, bool | None]:
            return {d: availability.get(d) for d in domains}

        async def _fake_ai(*, business_name: str, city: str | None, category: str | None) -> list[str]:
            return ai

        async def _fake_price(tld: str) -> float:
            if priced_tlds is not None:
                priced_tlds.append(tld)
            return 4.99

        monkeypatch.setattr(suggestion_module, "availability_map", _fake_map)
        monkeypatch.setattr(suggestion_module.llm_service, "suggest_domain_names", _fake_ai)
        monkeypatch.setattr(suggestion_module, "first_year_price_eur", _fake_price)
        return asyncio.run(
            domain_suggestion_service.suggest(
                name="Chez Mimon", city="Poitiers", category="restaurant", country=country
            )
        )

    def test_the_extension_follows_the_prospect_country(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A Swiss prospect gets ``.ch`` candidates priced as ``.ch``; France stays ``.fr``."""
        priced_tlds: list[str] = []
        switzerland = self._run_suggest(monkeypatch, availability={}, ai=[], country="CH", priced_tlds=priced_tlds)
        assert all(c.domain.endswith(".ch") for c in switzerland.candidates)
        assert priced_tlds == ["ch"]

        france = self._run_suggest(monkeypatch, availability={}, ai=[], country="FR")
        assert all(c.domain.endswith(".fr") for c in france.candidates)

    def test_prefers_the_first_available_candidate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        result = self._run_suggest(
            monkeypatch,
            availability={"chezmimon.fr": False, "chez-mimon.fr": True},
            ai=[],
        )
        assert result.suggested == "chez-mimon.fr"

    def test_falls_back_to_unknown_when_none_confirmed_free(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Top logical taken, the rest could not be checked → pre-fill the first unknown.
        result = self._run_suggest(monkeypatch, availability={"chezmimon.fr": False}, ai=[])
        assert result.suggested == "chez-mimon.fr"
        assert result.candidates[0] == DomainCandidate(
            domain="chezmimon.fr", available=False, price_eur=pytest.approx(4.99)
        )

    def test_appends_only_valid_ai_labels(self, monkeypatch: pytest.MonkeyPatch) -> None:
        result = self._run_suggest(
            monkeypatch,
            availability={},
            ai=["mimonresto", "nom invalide !!"],
        )
        domains = [c.domain for c in result.candidates]
        assert "mimonresto.fr" in domains
        assert all("invalide" not in d for d in domains)
