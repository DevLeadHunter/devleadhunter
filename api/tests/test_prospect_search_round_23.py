"""
Round 23 of the search training (the 120 sites of wave 5, read one by one): an acronym taken for a car dealer's, a
Swiss owner's first names read as his last name, owners the registry files under a commune's name, a hamlet or an
unnumbered street, a region's name taken for the business's, a firm struck off after moving its seat, a glued name
searched in the wrong département, an overseas commune written article last, owners' replies and page notices read
as reviews, and photos no site shows. Each case is a real one, its names, numbers and places replaced.
"""

import asyncio
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from enums.prospect_search import CandidateOrigin
from scrappers.enrichment_scraper import EnrichmentData, _customer_reviews
from scrappers.google_local_results import GoogleLocalResultsParser
from services.decision_maker.french_departments import FrenchDepartments
from services.decision_maker.normalize import join_dotted_initials
from services.decision_maker.strategies import RegistreGouvStrategy, TradeName
from services.decision_maker.swiss_register_people import SwissRegisterPeople
from services.decision_maker.types import ResolutionContext
from services.enrichment_service import EnrichmentService
from services.french_overseas import FrenchOverseas
from services.photo_labels import CRAFT_KIND_WORK, is_showable_craft_photo
from services.prospect_search.business_name import BusinessName
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.french_registry import FrenchRegistry, french_registry
from services.prospect_search.swiss_registry import SwissRegisterFirm, swiss_registry
from services.prospect_search.trade_catalog import TradeCatalog

_ELECTRICIAN = TradeCatalog.resolve("electricien")


def _company(name: str, *, activity: str, address: str, siren: str, head: tuple[str, str]) -> dict[str, Any]:
    """An open registry company of Ille-et-Vilaine, its seat at the given address."""
    last_name, first_name = head
    seat = {
        "adresse": address,
        "code_postal": address.split()[-2],
        "libelle_commune": address.split()[-1],
        "activite_principale": activity,
        "etat_administratif": "A",
    }
    return {
        "siren": siren,
        "nom_complet": name,
        "nom_raison_sociale": name,
        "nature_juridique": "5499",
        "etat_administratif": "A",
        "activite_principale": activity,
        "siege": seat,
        "matching_etablissements": [seat],
        "dirigeants": [
            {"nom": last_name, "prenoms": first_name, "qualite": "Gérant", "type_dirigeant": "personne physique"}
        ],
    }


def _registry(monkeypatch: pytest.MonkeyPatch, answers: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Script the registry's answers by query; returns the queries asked."""
    asked: list[str] = []

    async def search(
        query: str, *, department: str | None, per_page: int, activity_codes: list[str] | None = None
    ) -> list[dict[str, Any]]:
        asked.append(query)
        return answers.get(query, [])

    monkeypatch.setattr(RegistreGouvStrategy, "search", staticmethod(search))
    return asked


def test_an_acronym_registered_letters_apart_is_found_and_a_car_dealer_s_acronym_is_not_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """« EXC » is a car dealer's acronym in the town; the electrician is filed « E X C »."""
    car_dealer = _company(
        "EXEMPLE XPERT CARS (EXC)",
        activity="45.11Z",
        address="4 AVENUE MODELE 35999 EXEMPLEVILLE",
        siren="900000001",
        head=("MODELE", "PAUL"),
    )
    electrician = _company(
        "E X C",
        activity="43.21A",
        address="12 RUE EXEMPLE 35999 EXEMPLEVILLE",
        siren="900000002",
        head=("EXEMPLE", "JULES"),
    )
    asked = _registry(monkeypatch, {"EXC": [car_dealer], "E X C": [electrician]})
    context = ResolutionContext(
        company_name="EXC", city="Exempleville", postal_code="35999", trade="électricien", country="FR"
    )

    candidates = asyncio.run(RegistreGouvStrategy().resolve(context))

    assert asked == ["EXC", "E X C"]
    assert [(candidate.first, candidate.last) for candidate in candidates] == [("Jules", "Exemple")]


@pytest.mark.parametrize(
    ("name", "acronym"),
    [
        ("EXC", "EXC"),
        ("E.X.C", "EXC"),
        ("E X C", "EXC"),
        ("SARL EXC", "EXC"),
        ("Exemple Elec", None),
        ("EXEMPLE", None),
    ],
)
def test_an_acronym_is_read_whatever_its_dots_and_spaces(name: str, acronym: str | None) -> None:
    assert RegistreGouvStrategy.acronym_of(name) == acronym
    assert join_dotted_initials("E X C Elec") == "EXC Elec"


def test_among_companies_bearing_the_name_the_one_established_at_the_business_s_address_is_it() -> None:
    """Two « EXEMPLE PAYSAGES » in the département: the listing's address tells which."""
    at_its_address = _company(
        "EXEMPLE PAYSAGES",
        activity="81.30Z",
        address="12 RUE DES MODELES 35999 EXEMPLEVILLE",
        siren="900000003",
        head=("EXEMPLE", "JULES"),
    )
    elsewhere = _company(
        "EXEMPLE PAYSAGES",
        activity="81.30Z",
        address="8 ROUTE DU TEMOIN 35998 MODELEVILLE",
        siren="900000004",
        head=("TEMOIN", "PAUL"),
    )
    context = ResolutionContext(
        company_name="Exemple Paysages",
        city="Exempleville",
        postal_code="35999",
        trade="paysagiste",
        address="12 Rue des Modèles, 35999 Exempleville",
    )

    candidates = RegistreGouvStrategy().parse_results([elsewhere, at_its_address], context)

    assert [(candidate.first, candidate.last) for candidate in candidates] == [("Jules", "Exemple")]


@pytest.mark.parametrize(
    ("listing_street", "registered_address"),
    [
        ("30 rue des modeles", "LIEU DIT LE TEMOIN 30 RUE DES MODELES 35999 EXEMPLEVILLE"),
        ("impasse des exemples", "IMPASSE DE L EXEMPLE 35999 EXEMPLEVILLE"),
    ],
)
def test_a_registered_address_opening_on_a_hamlet_or_naming_its_street_in_the_singular_is_the_business_s(
    listing_street: str, registered_address: str
) -> None:
    company = _company(
        "JULES EXEMPLE", activity="81.30Z", address=registered_address, siren="900000005", head=("EXEMPLE", "JULES")
    )
    context = ResolutionContext(company_name="Exemple Jardins", city="Exempleville", postal_code="35999")

    assert RegistreGouvStrategy.has_establishment_at(company, listing_street, context=context, trade="paysagiste")


@pytest.mark.parametrize(
    ("address", "street"),
    [
        ("Imp. des Exemples, 35999 Exempleville", "impasse des exemples"),
        ("Chemin du Modèle, 35999 Exempleville", "chemin du modele"),
        ("12 Rue Exemple, 35999 Exempleville", None),
        ("Lieu Exemple, 35999 Exempleville", None),
        ("35999 Exempleville", None),
    ],
)
def test_an_address_opening_on_its_street_without_a_number_gives_that_street(address: str, street: str | None) -> None:
    assert RegistreGouvStrategy.unnumbered_street_of(address) == street


def test_a_listing_without_a_street_number_finds_its_owner_on_the_street_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    """« Exemple et Jardins » gives « Impasse des Exemples »: the sole trader seated there is proposed."""
    sole_trader = _company(
        "MODELE PAUL",
        activity="81.30Z",
        address="IMPASSE DES EXEMPLE 35999 EXEMPLEVILLE",
        siren="900000006",
        head=("MODELE", "PAUL"),
    )
    sole_trader["nature_juridique"] = "1000"
    asked = _registry(monkeypatch, {"impasse des exemples": [sole_trader]})
    context = ResolutionContext(
        company_name="Exemple et Jardins",
        city="Exempleville",
        postal_code="35999",
        trade="paysagiste",
        address="Impasse des Exemples, 35999 Exempleville",
    )

    candidates = asyncio.run(RegistreGouvStrategy().resolve(context))

    assert "impasse des exemples" in asked
    assert [(candidate.first, candidate.last, candidate.primary) for candidate in candidates] == [
        ("Paul", "Modele", False)
    ]


@pytest.mark.parametrize(("commune_department", "is_searched"), [("03", True), ("41", False)])
def test_a_word_naming_a_commune_of_another_departement_is_still_searched_as_the_owner_s_name(
    monkeypatch: pytest.MonkeyPatch, commune_department: str, is_searched: bool
) -> None:
    """« Exemplebourg Électricité » of the Loir-et-Cher: Exemplebourg is a commune of the Allier, and the owner's name."""

    async def communes_named(word: str) -> list[dict[str, str]]:
        return [{"nom": "Exemplebourg", "codeDepartement": commune_department}] if word == "exemplebourg" else []

    monkeypatch.setattr(FrenchDepartments, "_communes_named", staticmethod(communes_named))
    sole_trader = _company(
        "EXEMPLEBOURG JULES",
        activity="43.21A",
        address="3 RUE DU MODELE 41999 MODELEVILLE",
        siren="900000007",
        head=("EXEMPLEBOURG", "JULES"),
    )
    sole_trader["nature_juridique"] = "1000"
    asked = _registry(monkeypatch, {"exemplebourg": [sole_trader]})
    context = ResolutionContext(
        company_name="Exemplebourg Électricité", city="Modeleville", postal_code="41999", trade="électricien"
    )

    candidates = asyncio.run(RegistreGouvStrategy().resolve(context))

    assert ("exemplebourg" in asked) is is_searched
    assert [(candidate.first, candidate.last) for candidate in candidates] == (
        [("Jules", "Exemplebourg")] if is_searched else []
    )


def test_a_swiss_owner_listed_last_name_first_with_a_comma_keeps_his_first_names() -> None:
    """« Exemple, Jules Paul, de … » was read as Paul Jules: the lone last name was cut from its first names."""
    publication = (
        date(2025, 3, 4),
        "Exemple Électricité Sàrl, à Exempleville, CHE-111.222.333, société à responsabilité limitée (Nouvelle "
        "inscription). Personne(s) inscrite(s): Exemple, Jules Paul, de Modèleville, à Exempleville, associé gérant, "
        "avec signature individuelle, pour 20 parts sociales de CHF 1'000.00; Témoin, Anne, de Bex, à Bex, associée, "
        "sans droit de signature, pour 20 parts sociales de CHF 1'000.00.",
    )

    people = SwissRegisterPeople.registered_people([publication])

    assert [(person.first_name, person.last_name) for person in people] == [
        ("Jules Paul", "Exemple"),
        ("Anne", "Témoin"),
    ]


def test_a_firm_struck_off_after_moving_its_seat_closes_the_listing_left_at_its_old_seat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The gazette seated the firm in the listing's town before it moved; struck off since, it closes the business."""
    firm = SwissRegisterFirm(
        "Exemple Services Sàrl",
        "Modèleville",
        "GELOESCHT",
        "CHE-111.222.333",
        datetime.now(UTC).date() - timedelta(days=300),
        register_id=7,
    )

    async def firms_named(name: str, *, max_entries: int = 10) -> list[SwissRegisterFirm]:
        return [firm]

    async def page(listed_firm: SwissRegisterFirm) -> dict[str, object]:
        return {
            "shabPub": [
                {
                    "shabDate": "2014-02-03",
                    "message": "<p>Exemple Services Sàrl, à Exempleville, CHE-111.222.333, société à responsabilité "
                    "limitée (Nouvelle inscription).</p>",
                },
                {
                    "shabDate": "2016-06-20",
                    "message": "Exemple Services Sàrl, à Modèleville, CHE-111.222.333, société à responsabilité "
                    "limitée (Modification). Siège transféré.",
                },
            ]
        }

    monkeypatch.setattr(swiss_registry, "firms_named", firms_named)
    monkeypatch.setattr(swiss_registry, "_detail", page)
    facts = CandidateFacts(
        name="Exemple Services",
        trade_key="electricien",
        country="CH",
        origin=CandidateOrigin.GOOGLE_LOCAL.value,
        city="Exempleville",
    )

    asyncio.run(swiss_registry.read_closing(facts))

    assert facts.is_closed
    assert facts.evidence[-1]["fact"] == "closed"


@pytest.mark.parametrize(
    ("name", "region_words"),
    [
        ("E.X.E Grand Est Énergie", {"grand", "est"}),
        ("Exemple Jaden Matinik", {"matinik"}),
        ("Exemple Paysages Pays de la Loire", {"pays", "de", "la", "loire"}),
        ("Exemple Paysages", set()),
    ],
)
def test_a_region_a_name_carries_is_no_word_of_the_business_s_own(name: str, region_words: set[str]) -> None:
    assert BusinessName.region_words(name) == region_words
    assert not BusinessName.distinctive_words(name) & region_words


def test_a_company_found_by_a_region_s_name_is_not_the_business() -> None:
    """« Exemple Jaden Matinik » is searched as « Exemple Jaden »: « MATINIK ESPACES VERTS » is another landscaper."""
    assert TradeName.without_trade_words("Exemple Jaden Matinik") == "Exemple Jaden"
    assert not BusinessName.is_named_like("MATINIK ESPACES VERTS", "Exemple Jaden Matinik", town=None)


def test_a_page_named_after_the_same_region_is_not_the_business_s_page() -> None:
    facts = CandidateFacts(
        name="E.X.E Grand Est Énergie",
        trade_key="electricien",
        country="FR",
        origin=CandidateOrigin.GOOGLE_LOCAL.value,
        city="Exempleville",
    )

    assert not CandidateVerifier.names_business("Rénovation Grand Est", facts, _ELECTRICIAN)


@pytest.mark.parametrize(
    ("name", "searchable"),
    [
        ("EXPAYSAGES", "EX PAYSAGES"),
        ("exelec", "ex elec"),
        ("ExempleAuto64", "Exemple Auto 64"),
        ("ELECTRICITE", "ELECTRICITE"),
        ("JARDINS", "JARDINS"),
        ("Multiservices", "Multiservices"),
    ],
)
def test_a_trade_word_glued_to_the_name_is_set_apart_for_the_registry(name: str, searchable: str) -> None:
    assert TradeName.searchable(name) == searchable


def _listing_without_address(
    monkeypatch: pytest.MonkeyPatch, contact_place: str
) -> tuple[CandidateFacts, list[tuple[str, str | None]]]:
    """« EXPAYSAGES », found from Exempleville (Aude) without address, its page « EXPAYSAGES34 »."""

    async def communes_named(town: str) -> list[dict[str, str]]:
        return [{"nom": "Exempleville", "codeDepartement": "11"}] if town == "Exempleville" else []

    sole_trader = {
        "siren": "900000034",
        "nom_complet": "JULES MODELE (EX PAYSAGE)",
        "etat_administratif": "A",
        "nature_juridique": "1000",
        "dirigeants": [{"nom": "MODELE", "prenoms": "JULES"}],
        "siege": {"code_postal": "34999", "libelle_commune": "EXEMPLEBOURG", "activite_principale": "81.30Z"},
    }
    asked: list[tuple[str, str | None]] = []

    async def companies(query: str, *, department: str | None = None, **_options: object) -> list[dict[str, Any]]:
        asked.append((query, department))
        return [sole_trader] if (query, department) == ("EX PAYSAGES", "34") else []

    monkeypatch.setattr(FrenchDepartments, "_communes_named", staticmethod(communes_named))
    monkeypatch.setattr(FrenchRegistry, "_companies", staticmethod(companies))
    facts = CandidateFacts(
        name="EXPAYSAGES",
        trade_key="paysagiste",
        country="FR",
        origin=CandidateOrigin.GOOGLE_LOCAL.value,
        searched_city="Exempleville",
        email="expaysages@outlook.fr",
    )
    facts.add_evidence("contact_elsewhere", contact_place, source="Sa page Facebook")
    return facts, asked


def test_a_listing_without_address_is_looked_for_in_the_departement_its_page_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facts, asked = _listing_without_address(monkeypatch, "34")

    asyncio.run(french_registry.read_closing(facts))

    assert ("EX PAYSAGES", "34") in asked
    assert (facts.address, facts.city, facts.registry_number) == ("34999 Exemplebourg", "Exemplebourg", "900000034")
    assert facts.contact_elsewhere is None


def test_a_page_naming_a_region_sends_the_registry_nowhere_else(monkeypatch: pytest.MonkeyPatch) -> None:
    facts, asked = _listing_without_address(monkeypatch, "occitanie")

    asyncio.run(french_registry.read_closing(facts))

    assert {department for _query, department in asked} == {"11"}
    assert (facts.address, facts.contact_elsewhere is not None) == (None, True)


def test_an_overseas_commune_written_article_last_is_spelled_as_the_department_does() -> None:
    address = "13 Rue Exemple, ROBERT (LE 97231, Martinique"
    department = FrenchOverseas.of_address(address)

    assert department is not None
    assert department.commune_in(address) == "Le Robert"
    assert department.with_communes_spelled(address) == "13 Rue Exemple, Le Robert 97231, Martinique"
    assert department.with_communes_spelled("Garage (le meilleur), 97231 Le Robert") == (
        "Garage (le meilleur), 97231 Le Robert"
    )


def test_a_listing_of_martinique_keeps_its_commune_spelled_the_department_s_way() -> None:
    page = (
        '<html><body><div class="VkpGBb"><div><div class="rllt__details">'
        '<div role="heading"><span>Exemple Elec</span></div><div>5,0 (3) · Électricien</div></div></div>'
        '<a href="/maps/dir//Exemple+Elec,+13+Rue+Exemple,+ROBERT+(LE+97231,+Martinique/data=!4m6!4m5!1m1!4e2!1m2'
        '!1m1!1s0x8c6a:0x1a01?sa=X">Itinéraire</a></div></body></html>'
    )

    listing = GoogleLocalResultsParser.parse_html(page, country="FR")[0]

    assert listing.address == "13 Rue Exemple, Le Robert 97231, Martinique"


def test_an_owner_s_reply_or_a_page_notice_read_as_a_review_is_dropped() -> None:
    reviews = [
        {
            "author": "Jules Exemple",
            "rating": 5,
            "text": "Merci beaucoup Monsieur Exemple pour votre confiance, à très bientôt … Plus",
            "owner_response": "Il y a 3 mois\nMerci beaucoup Monsieur Exemple pour votre confiance, à très bientôt "
            "pour l'entretien du jardin.",
        },
        {"author": "Exemple Paysages", "text": "Pas encore évalué (1 avis)"},
        {"author": "Anne Modèle", "text": "Anne Modèle a limité qui peut commenter cette publication."},
        {
            "author": "Paul Témoin",
            "rating": 5,
            "text": "Très bon travail, équipe ponctuelle et soigneuse.",
            "owner_response": "Merci Paul pour votre confiance !",
        },
    ]

    assert [review["author"] for review in _customer_reviews(reviews)] == ["Paul Témoin"]


def test_the_enrichment_stores_no_owner_s_reply_as_a_review() -> None:
    record = SimpleNamespace(
        source="google_maps",
        rating=5.0,
        reviews_count=2,
        description=None,
        logo_url=None,
        photos=[],
        reviews=[],
        opening_hours=[],
        services=[],
        social_links={},
        place_title="Exemple Paysages",
        place_city="Exempleville",
        place_postal_code="35999",
    )
    scraped = EnrichmentData(
        source="google_maps",
        reviews=[
            {
                "author": "Jules Exemple",
                "rating": 5,
                "text": "Je vous remercie Monsieur Exemple pour votre confiance.",
                "owner_response": "Je vous remercie Monsieur Exemple pour votre confiance.",
            },
            {"author": "Paul Témoin", "rating": 5, "text": "Très bon travail, équipe ponctuelle et soigneuse."},
        ],
    )

    EnrichmentService()._apply_data(record, scraped)  # type: ignore[arg-type]

    assert [review["author"] for review in record.reviews] == ["Paul Témoin"]


@pytest.mark.parametrize(
    ("description", "is_showable"),
    [
        ("Interphone d'immeuble avec les noms des résidents", False),
        ("Boîtes aux lettres avec noms des locataires", False),
        ("Machine de nettoyage moteur Bardahl avec logo bien visible", False),
        ("Logo Motul sur une station de vidange", False),
        ("Câbles électriques emmêlés et fils en désordre dans un local technique", False),
        ("Tableau électrique neuf, câblage soigné et repéré", True),
        ("Pont élévateur dans l'atelier avec un véhicule en réparation", True),
    ],
)
def test_a_photo_showing_residents_names_a_supplier_s_logo_or_a_mess_is_never_shown(
    description: str, is_showable: bool
) -> None:
    label = {"family": "craft", "kind": CRAFT_KIND_WORK, "description": description, "appeal": 4}

    assert is_showable_craft_photo(label) is is_showable
