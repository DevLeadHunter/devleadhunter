"""
Who runs a Swiss business, read from its FOSC publications — the formats met on real firms (7 Oct 2026).

Every name here is invented: the publications keep the real wording, never a real person.
"""

from datetime import date

from services.decision_maker.swiss_register_people import RegisteredPerson, SwissRegisterPeople


def _leads(*publications: tuple[date, str]) -> list[tuple[str | None, str, bool]]:
    """The leading people of the publications, as (first name, last name, is the first name certain)."""
    people = SwissRegisterPeople.registered_people(list(publications))
    return [
        (person.first_name, person.last_name, person.is_name_certain)
        for person in SwissRegisterPeople.lead_people(people)
    ]


def test_a_sole_trader_is_its_holder() -> None:
    """« Personne(s) inscrite(s): Nom, Prénom, de …, à …, titulaire » — the modern format since about 2020."""
    publication = (
        date(2024, 7, 30),
        "Exemple Paysages, à Porrentruy, CHE-111.222.333, entreprise individuelle (Nouvelle inscription). "
        "But de l'entreprise: Paysagisme. Personne(s) inscrite(s): Exemple, Paul, de Haute-Ajoie, à "
        "Porrentruy, titulaire, avec signature individuelle.",
    )

    assert _leads(publication) == [("Paul", "Exemple", True)]


def test_the_older_holder_heading_writes_the_first_name_last() -> None:
    """« Titulaire: Exemple Paul, de … » — the first name after the last name."""
    publication = (
        date(2020, 4, 16),
        "Exemple Paysagiste, à Morges, CHE-111.222.333. Nouvelle entreprise individuelle. Titulaire: "
        "Exemple Paul, de La Sagne, à Morges, avec signature individuelle. But: horticulture et paysagisme.",
    )

    assert _leads(publication) == [("Paul", "Exemple", True)]


def test_a_chair_runs_the_company_before_a_manager() -> None:
    """« associé et président des gérants » outranks « associé et gérant »."""
    publication = (
        date(2021, 3, 1),
        "Personne(s) inscrite(s): Exemple, Paul, de Sion, à Ardon, associé et président des gérants, avec "
        "signature individuelle, pour 10 parts sociales de CHF 1'000.00; Modèle, Luc, de Bex, à Ardon, "
        "associé et gérant, avec signature individuelle, pour 10 parts sociales de CHF 1'000.00.",
    )

    assert _leads(publication) == [("Paul", "Exemple", True)]


def test_an_associate_also_manager_runs_the_company() -> None:
    """« Associé: Exemple Paul, …, lequel est en outre gérant avec signature individuelle »."""
    publication = (
        date(2023, 9, 18),
        "Capital social: CHF 20'000. Associé: Exemple Paul, de Rapperswil (BE), à La Chaux-de-Fonds, avec 20 "
        "parts sociales de CHF 1'000, lequel est en outre gérant avec signature individuelle. Organe de "
        "publication: Feuille officielle suisse du commerce.",
    )

    assert _leads(publication) == [("Paul", "Exemple", True)]


def test_a_manager_heading_with_its_signature_names_the_manager() -> None:
    """« Associé-gérant avec signature individuelle: Exemple Paul, de …, à …, avec 200 parts »."""
    publication = (
        date(2024, 12, 17),
        "Associé-gérant avec signature individuelle: Exemple Paul, de Vulliens, à Noville, avec 200 parts de "
        "CHF 100. Signature individuelle est conférée à Exemple Anne, de Vulliens, à Noville.",
    )

    assert _leads(publication) == [("Paul", "Exemple", True)]


def test_the_manager_named_after_the_associates_is_the_lead() -> None:
    """« Associés: …, et … . Gérant: l'associé Exemple Paul avec signature individuelle. »"""
    publication = (
        date(2016, 9, 8),
        "Associés: Exemple Paul, du Portugal, à Romont FR, avec 21 parts de CHF 500, et Modèle Anne, du "
        "Portugal, à Romont FR, avec 19 parts de CHF 500. Gérant: l'associé Exemple Paul avec signature "
        "individuelle. Selon déclaration du 02.09.2016, la société renonce à un contrôle restreint.",
    )

    assert _leads(publication) == [("Paul", "Exemple", True)]


def test_a_long_older_name_leaves_its_first_name_unsure() -> None:
    """« Exemple Modèle Jean Paul » cannot tell where the last name stops: the name is only proposed."""
    publication = (
        date(2016, 9, 8),
        "Gérant: l'associé Exemple Modèle Jean Paul avec signature individuelle. Fin.",
    )

    assert _leads(publication) == [("Paul", "Exemple Modèle Jean", False)]


def test_the_board_chair_of_an_older_list_runs_the_company() -> None:
    """« Administration: Exemple Paul, de …, à …, président, Modèle Luc, de …, à …, lesquels signent… »."""
    publication = (
        date(2025, 8, 28),
        "Administration: Exemple Paul, de Rochefort, à Cortaillod, président, Modèle Luc, de Neuchâtel, à "
        "Val-de-Travers, lesquels signent individuellement, et Témoin Anne, laquelle n'exerce plus la "
        "signature sociale.",
    )

    assert _leads(publication) == [("Paul", "Exemple", True)]


def test_a_person_who_left_no_longer_runs_the_company() -> None:
    """A later « … n'est plus gérant » or a striking-off section removes the person."""
    entered = (
        date(2019, 1, 10),
        "Personne(s) inscrite(s): Exemple, Paul, de Sion, à Sion, associé et gérant, avec signature "
        "individuelle; Modèle, Luc, de Sion, à Sion, associé, avec signature individuelle.",
    )
    left = (
        date(2022, 5, 3),
        "Personne(s) et signature(s) radiée(s): Exemple, Paul, de Sion, à Sion, associé et gérant, avec "
        "signature individuelle. Inscription ou modification de personne(s): Modèle, Luc, de Sion, à Sion, "
        "associé et gérant, avec signature individuelle.",
    )

    assert _leads(left, entered) == [("Luc", "Modèle", True)]


def test_a_departure_sentence_strikes_the_person_off() -> None:
    """« Exemple Paul n'est plus président; ses pouvoirs sont radiés. »"""
    entered = (
        date(2018, 1, 1),
        "Administration: Exemple Paul, de Bâle, à Bâle, président, avec signature individuelle.",
    )
    left = (date(2024, 1, 1), "Exemple Paul n'est plus président; ses pouvoirs sont radiés.")

    assert _leads(entered, left) == []


def test_mis_decoded_accents_are_repaired() -> None:
    """Some publications carry UTF-8 read as Latin-1: « Ã Porrentruy », « associÃ© »."""
    publication = (
        date(2026, 4, 16),
        "Personne(s) inscrite(s): Exemple, Paul, de Haute-Ajoie, Ã  Porrentruy, associÃ© et "
        "gÃ©rant, avec signature individuelle.",
    )

    people = SwissRegisterPeople.registered_people([publication])

    assert [(person.last_name, person.roles) for person in people] == [("Exemple", ("associé et gérant",))]


def test_an_auditing_company_is_no_person() -> None:
    """« Organe de révision: Fiduciaire Exemple SA » names no one to greet."""
    assert RegisteredPerson(first_name=None, last_name="Exemple", roles=("membre",)).rank == 0
    publication = (date(2020, 1, 1), "Personne(s) inscrite(s): Fiduciaire Exemple SA, à Sion, organe de révision.")

    assert SwissRegisterPeople.registered_people([publication]) == []
