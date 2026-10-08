"""
Where the head of a small business shows besides the registry it is filed under — its own email address, its
licence in the Québec registry, its owner's name in a French registry search within the trade — checked by hand
on 68 campaign leads that had no decision maker.

Every name here is invented.
"""

import asyncio

import pytest

from services.decision_maker.email_owner import EmailOwnerStrategy, PersonInEmail
from services.decision_maker.given_names import GivenNames
from services.decision_maker.normalize import infer_gender
from services.decision_maker.resolver import DecisionMakerResolver
from services.decision_maker.strategies import RbqOfficerStrategy, RegistreGouvStrategy, RegistryKeyword
from services.decision_maker.types import NameCandidate, NameResolution, ResolutionContext
from services.professional_license_service import RbqLicenceOfficer, RbqLicenseRegistryClient
from services.prospect_search.business_name import BusinessName


def _registry_company(name: str, **overrides: object) -> dict[str, object]:
    """An active sole trader of the Côte-d'Or declaring electrical work."""
    company: dict[str, object] = {
        "nom_complet": name,
        "nom_raison_sociale": None,
        "nature_juridique": "1000",
        "siren": "123456789",
        "etat_administratif": "A",
        "siege": {"code_postal": "21000", "libelle_commune": "DIJON", "activite_principale": "43.21A"},
        "dirigeants": [],
    }
    company.update(overrides)
    return company


def test_the_official_list_knows_the_first_names_the_old_one_missed() -> None:
    """« Franck », « Guy » or an Albanian « Arben » are first names; « Dominique » tells no sex; « garage » is none."""
    assert [GivenNames.is_given_name(word) for word in ("Franck", "Guy", "Arben", "garage")] == [
        True,
        True,
        True,
        False,
    ]
    assert (infer_gender("Franck"), infer_gender("Dominique"), infer_gender("Jean-Pierre")) == ("M", None, "M")


def test_an_address_named_after_a_person_names_them() -> None:
    """Dotted or glued, with a number or a trade word around it, the address spells the person who reads it."""
    readings = {
        "jules.modele@exemple.fr": "Modele Paysage",
        "julesmodele1975@exemple.fr": "Jules Modele Electrique Inc",
        "jardin.jules.modele@exemple.fr": "Entretien jardin Exempleville",
        "julesmodelejm@exemple.fr": "JM Paysage",
    }

    people = [PersonInEmail.person_of(email, business) for email, business in readings.items()]

    assert [(person.first_name, person.last_name, person.is_in_business_name) for person in people if person] == [
        ("Jules", "Modele", True),
        ("Jules", "Modele", True),
        ("Jules", "Modele", False),
        ("Jules", "Modele", True),
    ]


def test_an_address_of_the_business_names_nobody() -> None:
    """The business name repeated, a mailbox word, a first name alone (it may be a last name), initials, or a glued
    name the business name does not confirm (it may be a double last name) name nobody."""
    addresses = {
        "garagejulesmodele@exemple.fr": "Garage Jules Modele",
        "info@exemple.fr": "Modele Paysage",
        "jules_lps@exemple.fr": "Garage LP services",
        "julesm1990@exemple.fr": "Modele des Jardins",
        "julesmodele@exemple.fr": "Garage du Centre",
    }

    assert [PersonInEmail.person_of(email, business) for email, business in addresses.items()] == [None] * 5


def test_a_first_name_alone_takes_the_last_name_the_business_name_gives_it() -> None:
    """« julesxavier@ » at « Jules Modele Jardinier »: Jules Modele, named twice by the business."""
    person = PersonInEmail.person_of("julesxavier034@exemple.fr", "Jules Modele Jardinier")

    assert person is not None
    assert (person.first_name, person.last_name, person.is_in_business_name) == ("Jules", "Modele", True)


def test_a_person_the_business_names_twice_is_used_alone_another_is_proposed() -> None:
    """Email and business name agreeing make an automatic contact; an email alone stays a proposal."""
    resolver = DecisionMakerResolver(strategies=[])
    named_twice = EmailOwnerStrategy().candidates_of(
        ResolutionContext(company_name="Modele Paysage", emails=["jules.modele@exemple.fr"])
    )
    named_once = EmailOwnerStrategy().candidates_of(
        ResolutionContext(company_name="Garage du Centre", emails=["jules.modele@exemple.fr"])
    )

    assert resolver.pick_best(named_twice).status == NameResolution.AUTO
    assert resolver.pick_best(named_once).status == NameResolution.PROPOSED


def test_the_registry_officer_running_a_quebec_licence_is_the_head() -> None:
    """Of three officers, the one answering for administration and management runs it; a sole holder is a person."""
    payload = {
        "retour": {
            "intervenant": {"nom": "Entreprises Electriques Exemple inc."},
            "dirigeants": [
                {"interlocuteurDirigeant": {"prenom": "Paul", "nom": "Modele", "indAdministration": False}},
                {
                    "interlocuteurDirigeant": {
                        "prenom": "Jules",
                        "nom": "Modele",
                        "indAdministration": True,
                        "indGestion": True,
                    }
                },
            ],
        }
    }
    holder_payload = {"retour": {"intervenant": {"nom": "Temoin, Anne"}, "dirigeants": []}}

    officers = RbqLicenseRegistryClient.parse_officers(payload)
    candidates = RbqOfficerStrategy().candidates_of(officers, licence_number="1234-5678-90")

    assert [(c.first, c.last, c.anchored, c.confidence) for c in candidates] == [("Jules", "Modele", True, 0.9)]
    assert RbqLicenseRegistryClient.parse_officers(holder_payload) == [
        RbqLicenceOfficer(first_name="Anne", last_name="Temoin", runs_the_business=True)
    ]


def test_two_officers_running_a_licence_are_only_proposed() -> None:
    """Two equal heads: the first is proposed, never used alone."""
    officers = [
        RbqLicenceOfficer(first_name="Jules", last_name="Modele", runs_the_business=True),
        RbqLicenceOfficer(first_name="Anne", last_name="Temoin", runs_the_business=True),
    ]

    candidates = RbqOfficerStrategy().candidates_of(officers, licence_number="1234-5678-90")

    assert DecisionMakerResolver(strategies=[]).pick_best(candidates).status == NameResolution.PROPOSED


def test_the_company_bearing_the_exact_name_leaves_out_the_others_of_its_words() -> None:
    """« EXEMPLE 05 » is the business; « VENTE EXEMPLE 05 » and « CASSE EXEMPLE 05 » are other garages."""
    context = ResolutionContext(company_name="Exemple 05", city="Gap", postal_code="05000")
    siege = {"code_postal": "05000", "libelle_commune": "GAP", "activite_principale": "45.20A"}
    results = [
        _registry_company("VENTE EXEMPLE 05", siege=siege, dirigeants=[{"nom": "TEMOIN", "prenoms": "Anne"}]),
        _registry_company(
            "EXEMPLE 05", siege=siege, nature_juridique="5499", dirigeants=[{"nom": "MODELE", "prenoms": "Jules"}]
        ),
        _registry_company("CASSE EXEMPLE 05", siege=siege, dirigeants=[{"nom": "MODELE", "prenoms": "Paul"}]),
    ]

    candidates = RegistreGouvStrategy().parse_results(results, context, department="05")

    assert [(candidate.first, candidate.last) for candidate in candidates] == [("Jules", "Modele")]


def test_a_company_found_by_a_word_of_the_business_must_be_of_its_trade_in_its_departement() -> None:
    """« EXEMPLE » finds the electrician filed as « JULES MODELE (EXEMPLE) »; a cleaner or a Lyon firm is another."""
    strategy = RegistreGouvStrategy()
    context = ResolutionContext(company_name="EXEMPLE Electrical", city="Dijon")
    own = _registry_company("JULES MODELE (EXEMPLE)")
    cleaner = _registry_company("EXEMPLE NETTOYAGE", siege={"code_postal": "21000", "activite_principale": "81.21Z"})
    elsewhere = _registry_company("EXEMPLE", siege={"code_postal": "69003", "activite_principale": "43.21A"})

    checks = [
        strategy.is_keyword_company(
            company, RegistryKeyword("exemple"), context=context, trade="électricien", department="21"
        )
        for company in (own, cleaner, elsewhere)
    ]

    assert checks == [True, False, False]


def test_a_company_found_by_a_common_word_must_bear_no_other_name() -> None:
    """« parc » of « Modele Entretien parc et jardin » finds « TEMOIN PARC ET JARDIN », another landscaper."""
    strategy = RegistreGouvStrategy()
    context = ResolutionContext(company_name="Modele Entretien parc et jardin", city="Limoges")
    siege = {"code_postal": "87000", "activite_principale": "81.30Z"}
    another = _registry_company("ANNE TEMOIN (TEMOIN PARC ET JARDIN)", siege=siege)
    named_after_its_holder = _registry_company(
        "JULES MODELE", siege=siege, dirigeants=[{"nom": "MODELE", "prenoms": "Jules"}]
    )

    assert not strategy.is_keyword_company(
        another, RegistryKeyword("parc"), context=context, trade="paysagiste", department="87"
    )
    assert strategy.is_keyword_company(
        named_after_its_holder, RegistryKeyword("modele"), context=context, trade="paysagiste", department="87"
    )


def test_a_company_found_by_its_owner_must_be_run_by_him() -> None:
    """The person an email or a review names must be the sole trader or a manager of the company found."""
    strategy = RegistreGouvStrategy()
    sole_trader = _registry_company("JULES MODELE")
    managed = _registry_company(
        "EXEMPLE ELEC", nature_juridique="5499", dirigeants=[{"nom": "MODELE", "prenoms": "Jules Henri"}]
    )
    another = _registry_company("ANNE TEMOIN")

    checks = [
        strategy.is_keyword_company(
            company,
            RegistryKeyword("Modele", person=(None, "Modele")),
            context=ResolutionContext(company_name="ABC électricité"),
            trade="électricien",
            department="21",
        )
        for company in (sole_trader, managed, another)
    ]

    assert checks == [True, True, False]


def test_customers_saying_monsieur_give_the_last_name_to_search() -> None:
    """« mr Modele », « M. Modele » or « Madame Temoin » in reviews: each last name is a registry query."""
    context = ResolutionContext(
        company_name="ABC électricité",
        review_texts=["Travail soigné de mr Modele.", "M. Modele est ponctuel. Merci à Madame Temoin."],
    )

    keywords = [keyword.text for keyword in RegistreGouvStrategy._keywords(context) if keyword.person is not None]

    assert keywords == ["Modele", "Temoin"]


def test_a_property_company_bearing_the_business_name_is_its_landlord() -> None:
    """« SCI DE L'EXEMPLE » owns the premises of « Garage de l'Exemple »: never the business."""
    context = ResolutionContext(company_name="Garage de l'Exemple", city="Dijon", postal_code="21000")
    landlord = _registry_company(
        "SCI DE L EXEMPLE", nature_juridique="6540", dirigeants=[{"nom": "MODELE", "prenoms": "Jules"}]
    )

    assert RegistreGouvStrategy().parse_results([landlord], context, department="21") == []
    assert not BusinessName.is_exact_name("SCI DE L EXEMPLE", "Garage de l'Exemple")
    assert BusinessName.is_exact_name("ABC EXEMPLE & PISCINE", "ABC Exemple & Piscine")


def test_plural_and_feminine_spellings_of_a_name_are_the_same_name() -> None:
    """« Arbres aux paysages Exemple » is « Arbre aux paysages Exemple »; « Extérieure » is « Extérieur »."""
    assert BusinessName.is_named_like("Arbres aux paysages Exemple", "Arbre aux paysages Exemple", town=None)
    assert BusinessName.is_named_like("Exemple Aménagement Extérieure", "Exemple Aménagement Extérieur", town=None)


def test_the_resolution_reads_the_email_and_the_licence_of_the_business() -> None:
    """The cascade outside France reads the licence registry and the email address of the business."""
    from services.decision_maker.resolver import public_text_resolver

    names = {strategy.name for strategy in public_text_resolver.strategies}

    assert {"email", "registre_rbq"} <= names
    assert asyncio.run(RbqOfficerStrategy().resolve(ResolutionContext(company_name="Exemple"))) == []


def test_a_self_declared_name_contradicted_by_the_registry_is_only_proposed() -> None:
    """A registry naming someone else makes the email's person a proposal, never an automatic contact."""
    email_candidate = EmailOwnerStrategy().candidates_of(
        ResolutionContext(company_name="Modele Paysage", emails=["jules.modele@exemple.fr"])
    )
    registry_candidate = NameCandidate(
        first="Anne", last="Temoin", source="registre_gouv", confidence=0.7, primary=True, evidence_group="registry"
    )

    resolution = DecisionMakerResolver(strategies=[]).pick_best([*email_candidate, registry_candidate])

    assert resolution.status == NameResolution.PROPOSED


def test_the_business_email_domain_is_a_registry_query_a_mailbox_provider_is_not() -> None:
    """« …@exempelec.fr » names the company; « …@gmail.com » names nobody."""
    context = ResolutionContext(
        company_name="Exempelecelectricitelyon", emails=["electricite@exempelec.fr", "jules@gmail.com"]
    )

    keywords = RegistreGouvStrategy._keywords(context)

    assert [keyword.text for keyword in keywords if keyword.is_email_domain] == ["exempelec"]
    assert all("gmail" not in keyword.text for keyword in keywords)


def test_a_company_named_after_the_family_must_still_be_of_the_trade() -> None:
    """« Exemple des Jardins » is not the painter of the Exemple family the web search led to."""
    from services.decision_maker.strategies import WebRegistryStrategy

    context = ResolutionContext(company_name="Exemple des Jardins", city="Limoges", trade="paysagiste")
    painter = NameCandidate(
        first="Jules",
        last="Exemple",
        source="registre_gouv",
        primary=True,
        raw={"nom_complet": "JULES EXEMPLE", "activite": "43.34Z"},
    )
    gardener = NameCandidate(
        first="Paul",
        last="Exemple",
        source="registre_gouv",
        primary=True,
        raw={"nom_complet": "PAUL EXEMPLE", "activite": "81.30Z"},
    )

    assert [WebRegistryStrategy.is_company_of(candidate, context) for candidate in (painter, gardener)] == [False, True]


def test_a_signature_no_one_is_given_as_a_first_name_is_no_person() -> None:
    """« Avatacar », the booking platform answering reviews for the garage, is not its owner."""
    from services.decision_maker.strategies import OwnerResponseStrategy

    platform = ResolutionContext(
        company_name="Exemple 05", owner_responses=["Merci !\nAvatacar", "À bientôt\nAvatacar"]
    )
    owner = ResolutionContext(company_name="Exemple 05", owner_responses=["Merci !\nJules", "À bientôt\nJules"])

    assert asyncio.run(OwnerResponseStrategy().resolve(platform)) == []
    assert [candidate.first for candidate in asyncio.run(OwnerResponseStrategy().resolve(owner))] == ["Jules"]


def test_among_the_family_the_company_of_the_trade_s_main_activity_is_the_business(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """« Monsieur Modele » in reviews: the electrician Modele (43.21A), not the builder Modele (43.99C)."""

    async def registry_answer(query: str, **_filters: object) -> list[dict[str, object]]:
        return [
            _registry_company("PAUL MODELE", siege={"code_postal": "21000", "activite_principale": "43.99C"}),
            _registry_company("JULES MODELE", dirigeants=[{"nom": "MODELE", "prenoms": "Jules"}]),
        ]

    monkeypatch.setattr(RegistreGouvStrategy, "_search", staticmethod(registry_answer))
    context = ResolutionContext(
        company_name="ABC électricité", review_texts=["Monsieur Modele est sérieux."], trade="électricien"
    )

    candidates = asyncio.run(RegistreGouvStrategy()._search_by_keywords(context, "21"))

    assert [(candidate.first, candidate.last) for candidate in candidates] == [("Jules", "Modele")]


def test_a_word_naming_a_town_is_never_searched_as_the_business(monkeypatch: pytest.MonkeyPatch) -> None:
    """« Garage Pau-Lescar »: « Lescar » is a commune, and the garage the registry files there is another one."""
    from services.decision_maker.french_departments import FrenchDepartments

    async def communes_named(town: str) -> list[dict[str, str]]:
        return [{"nom": "Lescar", "codeDepartement": "64"}] if town.lower() == "lescar" else []

    async def registry_answer(query: str, **_filters: object) -> list[dict[str, object]]:
        siege = {"code_postal": "64230", "activite_principale": "45.20A"}
        return [
            _registry_company(f"GP {query.upper()}", siege=siege, dirigeants=[{"nom": "MODELE", "prenoms": "Jules"}])
        ]

    monkeypatch.setattr(FrenchDepartments, "_communes_named", staticmethod(communes_named))
    monkeypatch.setattr(RegistreGouvStrategy, "_search", staticmethod(registry_answer))
    context = ResolutionContext(company_name="Garage Pau-Lescar", city="Pau", trade="garage")

    candidates = asyncio.run(RegistreGouvStrategy()._search_by_keywords(context, "64"))

    assert candidates == []


def test_a_rare_first_name_can_be_the_last_name_of_an_address() -> None:
    """« anne.marty@ »: « Marty » is mostly a last name, so the address names Anne Marty."""
    person = PersonInEmail.person_of("anne.marty@exemple.fr", "Garage du Centre")

    assert person is not None
    assert (person.first_name, person.last_name) == ("Anne", "Marty")


def test_a_short_first_name_in_the_address_is_the_registry_s_person() -> None:
    """« exemple.fred@ » is « Frederic Exemple » of the registry: it confirms him, never demotes him."""
    registry_candidate = NameCandidate(
        first="Frederic",
        last="Exemple",
        source="registre_gouv",
        confidence=0.9,
        primary=True,
        geo_confirmed=True,
        evidence_group="registry",
        anchored=True,
    )
    email_candidates = EmailOwnerStrategy().candidates_of(
        ResolutionContext(company_name="F.E ELEC", emails=["exemple.fred@exemple.fr"])
    )

    resolution = DecisionMakerResolver(strategies=[]).pick_best([registry_candidate, *email_candidates])

    assert [candidate.first for candidate in email_candidates] == ["Fred"]
    assert (resolution.status, resolution.candidate.first if resolution.candidate else None) == (
        NameResolution.AUTO,
        "Frederic",
    )


def test_a_name_saying_more_than_a_family_name_skips_the_activity_check() -> None:
    """« JULES MODELE » is « Jules Modele Paysagiste » whatever its code; « MODELE » is not « Garage Modele »."""
    from types import SimpleNamespace

    from services.enrichment_service import EnrichmentService

    landscaper = SimpleNamespace(name="Jules Modele Paysagiste", city="Dijon", category="paysagiste")
    garage = SimpleNamespace(name="Garage Modele", city="Dijon", category="garage")
    sole_trader = NameCandidate(
        first="Jules",
        last="Modele",
        source="registre_gouv",
        primary=True,
        raw={"nom_complet": "JULES MODELE", "activite": "81.21Z"},
    )
    plumber = NameCandidate(
        first="Paul",
        last="Modele",
        source="registre_gouv",
        primary=True,
        raw={"nom_complet": "MODELE", "activite": "43.22A"},
    )

    assert EnrichmentService._activity_check(landscaper, sole_trader) == (None, None)
    assert EnrichmentService._activity_check(garage, plumber)[0] is False
