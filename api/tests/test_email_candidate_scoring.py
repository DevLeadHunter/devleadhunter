"""
Unit tests for EmailCandidateScorer — the town-hall / directory false-positive
rejection that replaced the old "first non-blacklisted email wins" behaviour.

All offline: the scorer only reads page text, never the network.

Léo's philosophy under test:
  - hard-reject ONLY provable non-prospects (state / mairie / directory / socials
    / domain-equals-city);
  - never reject on name↔domain incoherence (a footballer-named gmail is valid);
  - floor rule: as long as one candidate survives, return the best, even low-scored.
"""

import pytest

from scrappers.email_candidate_scoring import EmailCandidateScorer

scorer = EmailCandidateScorer()


def _only(email: str, *, name: str = "Garage Test", city: str = "Villeurbanne") -> str | None:
    """Best email of a page holding a single address (isolates disqualification)."""
    return scorer.best_email(f"Un resultat quelconque {email} fin de page", name=name, city=city)


# ── The ticket's real bug: mairie on top, real garage email below ────────────


def test_town_hall_email_never_beats_the_real_garage_email() -> None:
    """The Saint-Germain-Lembron case: mairie domain == city → dropped."""
    page = (
        "Mairie de Saint-Germain-Lembron — contact@saint-germain-lembron.fr — "
        "horaires d'ouverture. "
        "Garage Debiolle Patrick, 47 Rte d'Issoire — garage.debiolle@orange.fr"
    )
    best = scorer.best_email(page, name="Debiolle Patrick", city="Saint-Germain-Lembron")
    assert best == "garage.debiolle@orange.fr"


def test_domain_equal_to_city_is_rejected() -> None:
    """A vanity domain that IS the commune name is a town hall / office."""
    assert _only("contact@saint-germain-lembron.fr", city="Saint-Germain-Lembron") is None


def test_city_in_gmail_local_part_is_kept() -> None:
    """Léo's point: `leo.rennes@gmail.com` is legitimate — city in the LOCAL part."""
    assert _only("leo.rennes@gmail.com", name="Coiffure X", city="Rennes") == "leo.rennes@gmail.com"


# ── Hard-reject families (Temps 1) ───────────────────────────────────────────


def test_state_and_collectivity_domains_are_rejected() -> None:
    """gouv.fr, service-public.fr, mairie-*, ville-*, cc-*, ccas-* never a prospect."""
    assert _only("contact@ville-lyon.gouv.fr") is None
    assert _only("accueil@service-public.fr") is None
    assert _only("mairie@mairie-lembron.fr") is None
    assert _only("contact@ville-clermont.fr") is None
    assert _only("secretariat@cc-pays-de-lembron.fr") is None


def test_tourist_office_domains_are_rejected() -> None:
    """Office de tourisme shapes: ot-*, *-tourisme.fr."""
    assert _only("contact@ot-paysdelembron.com") is None
    assert _only("info@lembron-tourisme.fr") is None


def test_known_directories_and_socials_are_rejected() -> None:
    """Directory / aggregator / social domains are never the business contact."""
    for email in (
        "pro@pagesjaunes.fr",
        "garage@vroomly.com",
        "contact@allogarage.fr",
        "x@118000.fr",
        "page@facebook.com",
    ):
        assert _only(email) is None, email


def test_noreply_and_html_artifacts_are_rejected() -> None:
    """Role-noise local parts and HTML entity remnants are dropped."""
    assert _only("noreply@brevo.com") is None
    assert _only("u003e-garbage@example.com") is None


# ── Floor rule: never lose a prospect over a low score ───────────────────────


def test_unrelated_generic_email_survives_the_floor() -> None:
    """An email with zero link to name/city (footballer inbox) is STILL returned."""
    best = scorer.best_email(
        "Garage Dupont a Lyon — zizou.madrid@gmail.com",
        name="Garage Dupont",
        city="Lyon",
    )
    assert best == "zizou.madrid@gmail.com"


def test_returns_none_only_when_everything_is_disqualified() -> None:
    """No survivor → None (a clean 'no email', which existing guards filter out)."""
    page = "contact@mairie-lyon.fr et aussi info@pagesjaunes.fr"
    assert scorer.best_email(page, name="Garage Dupont", city="Lyon") is None


def test_empty_page_returns_none() -> None:
    """No email at all → None."""
    assert scorer.best_email("aucune adresse ici", name="X", city="Y") is None


# ── Ranking signals (Temps 2) ────────────────────────────────────────────────


def test_website_domain_match_wins() -> None:
    """The prospect's own website domain is the strongest ownership signal."""
    page = "voisin-random@gmail.com puis Plomberie Sud contact@plomberie-sud.fr"
    best = scorer.best_email(
        page,
        name="Plomberie Sud",
        city="Aix",
        website="https://www.plomberie-sud.fr",
    )
    assert best == "contact@plomberie-sud.fr"


def test_name_in_local_part_beats_an_unrelated_generic() -> None:
    """`garage.debiolle@orange.fr` outranks a neighbour's generic gmail."""
    page = "voisin.random@gmail.com et garage.debiolle@orange.fr"
    best = scorer.best_email(page, name="Garage Debiolle", city="Issoire")
    assert best == "garage.debiolle@orange.fr"


def test_proximity_breaks_ties_between_bare_generics() -> None:
    """With no domain/local signal, the email nearest the business name wins."""
    filler = " lorem ipsum dolor " * 120  # ~2000 chars, no name token inside
    page = f"loin@example-mail.fr{filler}Boulangerie Martin proche@contact-mail.fr"
    best = scorer.best_email(page, name="Boulangerie Martin", city="Nantes")
    assert best == "proche@contact-mail.fr"


def test_foreign_directories_are_never_the_artisan_email() -> None:
    """local.ch, pagesjaunes.ca and their peers list the artisan; their address is the directory's."""
    for email in (
        "info@local.ch",
        "contact@localsearch.ch",
        "info@pagesjaunes.ca",
        "service@411.ca",
        "info@goldenpages.be",
        "contact@editus.lu",
    ):
        assert _only(email, name="Sanitaire Rochat", city="Lausanne") is None, email


def test_a_directory_subdomain_is_rejected_like_its_domain() -> None:
    assert _only("info@tel.search.ch", name="Sanitaire Rochat", city="Lausanne") is None
    assert _only("info@mylocal.ch", name="Sanitaire Rochat", city="Lausanne") == "info@mylocal.ch"


def test_a_local_ch_listing_never_beats_the_swiss_plumber_email() -> None:
    page = "Sanitaire Rochat, Lausanne : info@local.ch. Plus d'infos sur la fiche. Écrire à atelier.lausanne@bluewin.ch"
    assert scorer.best_email(page, name="Sanitaire Rochat", city="Lausanne") == "atelier.lausanne@bluewin.ch"


def test_foreign_state_and_canton_domains_are_rejected() -> None:
    for email in (
        "info@bk.admin.ch",
        "contact@etat.ge.ch",
        "info@vd.ch",
        "info@economie.fgov.be",
        "contact@belgium.be",
        "guichet@guichet.public.lu",
        "info@canada.gc.ca",
        "req@registreentreprises.gouv.qc.ca",
        "311@ville.montreal.qc.ca",
    ):
        assert _only(email, name="Plomberie Tremblay", city="Laval") is None, email
    assert _only("contact@sysadmin.ch", name="Sysadmin", city="Genève") == "contact@sysadmin.ch"


def test_a_quebec_provincial_domain_is_split_after_qc_ca() -> None:
    assert EmailCandidateScorer._registrable_label("plomberie-tremblay.qc.ca") == "plomberie-tremblay"
    assert EmailCandidateScorer._registrable_label("info.plomberie-tremblay.qc.ca") == "plomberie-tremblay"
    assert EmailCandidateScorer._registrable_label("saint-germain-lembron.fr") == "saint-germain-lembron"


def test_two_qc_ca_domains_no_longer_share_the_website_bonus() -> None:
    page = "voisin@toitures-gagnon.qc.ca puis Plomberie Tremblay jean@plomberie-tremblay.qc.ca"
    best = scorer.best_email(page, name="Garage X", city="Laval", website="https://www.plomberie-tremblay.qc.ca")
    assert best == "jean@plomberie-tremblay.qc.ca"


def test_a_qc_ca_town_hall_named_after_the_city_is_rejected() -> None:
    assert _only("info@montreal.qc.ca", name="Plomberie Tremblay", city="Montréal") is None


def test_a_field_label_glued_to_the_address_is_not_part_of_it() -> None:
    """Seen on local.ch: the Google snippet writes « Emailjean.dupont@gmail.com »."""
    page = "Histoire d'un jardin Emailsebastien.mosimann@gmail.com puis E-Mailpaul@bluewin.ch"
    ranked = [email for email, _ in scorer.rank_candidates(page, name="Histoire d'un jardin", city="Vevey")]
    assert ranked == ["sebastien.mosimann@gmail.com", "paul@bluewin.ch"]


def test_an_address_that_starts_with_the_word_email_is_left_whole() -> None:
    assert _only("emailing@atelier-dupont.fr", name="Atelier Dupont", city="Lyon") == "emailing@atelier-dupont.fr"


def test_a_capitalised_address_starting_with_mail_is_left_whole() -> None:
    assert (
        _only("Maillard.plomberie@orange.fr", name="Maillard Plomberie", city="Dijon") == "maillard.plomberie@orange.fr"
    )
    assert _only("Mailys.dupont@gmail.com", name="Jardins Dupont", city="Dijon") == "mailys.dupont@gmail.com"


def test_the_email_label_a_directory_glues_to_the_address_is_still_detached() -> None:
    assert _only("Emailgarage.dupont@orange.fr", name="Garage Dupont", city="Lyon") == "garage.dupont@orange.fr"


def test_a_platform_or_a_data_protection_inbox_is_never_the_business_email() -> None:
    assert _only("dpo@plus-que-pro.fr", name="Winterstein Elagueur Paysagiste") is None
    assert _only("dpo@garage-martin.fr", name="Garage Martin") is None
    assert _only("contact@habitatpresto.com", name="Garage Martin") is None
    assert _only("contact@motrio.fr", name="Garage de l'Europe") is None
    assert _only("pdv06298@mousquetaires.com", name="Drapeau Automobiles") is None
    assert _only("info@autodistribution.com", name="Garage Martin") is None
    assert _only("contact@garage-martin.fr", name="Garage Martin") == "contact@garage-martin.fr"


@pytest.mark.parametrize(
    "email",
    ["paul.rochat@fri-cath.ch", "secretariat@cath-vd.ch", "accueil@paroisse-exemple.ch", "info@eglise-exemple.fr"],
)
def test_a_church_or_parish_address_belongs_to_an_institution(email: str) -> None:
    assert scorer.belongs_to_an_institution(email, city="Fribourg") is True


def test_a_name_starting_like_a_church_word_is_no_institution() -> None:
    assert scorer.belongs_to_an_institution("info@catherine-jardins.ch", city="Fribourg") is False
