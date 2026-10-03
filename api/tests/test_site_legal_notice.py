"""The legal block of a generated site: what its legal page says, country by country, on a demo and once sold."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from api.v1.routes.demo_sites import get_public_demo_site
from enums.contact_name_status import ContactNameStatus, ProposedContactState
from enums.demo_site_status import DemoSiteStatus
from enums.order_status import OrderStatus
from models.demo_site import DemoSite
from models.order import Order
from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from models.user import User
from schemas.site_legal_notice import SiteLegalBlock, SiteLegalNotice, SiteLegalSection
from services.country_profiles import CountryProfiles
from services.site_legal.notice_service import SiteLegalNoticeService
from services.site_legal.sources import (
    BusinessLegalIdentity,
    DemoPublisherIdentity,
    SiteLegalSourceLoader,
    SiteLegalSources,
)
from services.templates import registry

_PUBLISHER = DemoPublisherIdentity(
    name="Alexis Durand",
    company_name="Atelier Web Durand",
    postal_address="4 rue des Lilas, 35000 Rennes",
    email="contact@atelier-web.example",
    phone="06 12 34 56 78",
    website_url="https://atelier-web.example",
)


def _notice(
    country: str,
    business: BusinessLegalIdentity,
    *,
    is_demo: bool,
    template_id: str = "plumber-signature",
) -> SiteLegalNotice:
    return SiteLegalNoticeService.build(
        SiteLegalSources(
            country=CountryProfiles.get(country),
            is_demo=is_demo,
            business=business,
            publisher=_PUBLISHER if is_demo else None,
            visitor_data=registry.visitor_data(template_id),
        )
    )


def _section(notice: SiteLegalNotice, index: int) -> SiteLegalSection:
    return notice.sections[index]


def _block(section: SiteLegalSection, heading: str) -> SiteLegalBlock:
    return next(block for block in section.blocks if block.heading == heading)


def _headings(section: SiteLegalSection) -> list[str]:
    return [block.heading for block in section.blocks]


def _rendered(block: SiteLegalBlock) -> list[str]:
    return [f"{line.label} : {line.text}" if line.label else line.text for line in block.lines]


def _all_text(notice: SiteLegalNotice) -> str:
    texts = [notice.page_title, notice.demo_notice or ""]
    for section in notice.sections:
        texts.append(section.title)
        for block in section.blocks:
            texts.append(block.heading)
            texts.extend(_rendered(block))
    return "\n".join(texts)


def test_a_french_delivered_site_names_its_publisher_its_director_and_its_host() -> None:
    notice = _notice(
        "FR",
        BusinessLegalIdentity(
            name="SARL Plomberie Durand",
            trade_name="Durand Plomberie",
            address="8 rue de Brest, 35000 Rennes",
            phone="06 11 22 33 44",
            email="contact@durand.example",
            legal_id="123 456 789 00012",
            vat_number="FR32123456789",
            publication_director="Alexis Durand",
        ),
        is_demo=False,
    )

    legal = _section(notice, 0)
    assert notice.locale == "fr-FR"
    assert notice.demo_notice is None
    assert [(link.label, link.anchor) for link in notice.links] == [
        ("Mentions légales", "mentions-legales"),
        ("Confidentialité", "politique-de-confidentialite"),
    ]
    assert _headings(legal) == ["Éditeur du site", "Directeur de la publication", "Hébergeur"]
    assert _rendered(_block(legal, "Éditeur du site")) == [
        "SARL Plomberie Durand",
        "Nom commercial : Durand Plomberie",
        "8 rue de Brest, 35000 Rennes",
        "Téléphone : 06 11 22 33 44",
        "E‑mail : contact@durand.example",
        "SIRET : 123 456 789 00012",
        "TVA intracommunautaire : FR32123456789",
    ]
    assert _block(legal, "Éditeur du site").lines[3].href == "tel:+33611223344"
    assert _rendered(_block(legal, "Directeur de la publication")) == ["Alexis Durand"]
    host = _block(legal, "Hébergeur")
    assert _rendered(host)[:3] == [
        "Vercel Inc.",
        "440 N Barranca Avenue #4133, Covina, CA 91723, États-Unis",
        "Téléphone : +1 559 288 7060",
    ]


def test_a_french_delivered_site_privacy_policy_tells_what_the_form_does_and_measures_nothing() -> None:
    notice = _notice(
        "FR", BusinessLegalIdentity(name="Durand Plomberie", email="contact@durand.example"), is_demo=False
    )

    privacy = _section(notice, 1)
    text = _all_text(notice)
    assert privacy.title == "Politique de confidentialité"
    assert _headings(privacy)[0] == "Responsable du traitement"
    form = " ".join(_rendered(_block(privacy, "Formulaire de contact")))
    assert "il ouvre votre messagerie avec un e‑mail prérempli, adressé à Durand Plomberie" in form
    assert "article 6, paragraphe 1, point b, du RGPD" in form
    assert "au plus trois ans après le dernier contact" in form
    assert "Ce site ne mesure pas son audience et ne dépose aucun cookie." in text
    assert "PostHog" not in text
    assert "Vercel, Google et Cloudflare sont certifiés selon le Data Privacy Framework UE-États-Unis" in text
    rights = _block(privacy, "Vos droits")
    assert rights.lines[-1].text == "Commission nationale de l'informatique et des libertés (CNIL)"
    assert rights.lines[-1].href == "https://www.cnil.fr"


def test_a_french_site_without_known_identifier_or_director_invents_neither() -> None:
    notice = _notice("FR", BusinessLegalIdentity(name="Durand Plomberie", phone="06 11 22 33 44"), is_demo=False)

    legal = _section(notice, 0)
    assert _headings(legal) == ["Éditeur du site", "Hébergeur"]
    assert _rendered(_block(legal, "Éditeur du site")) == ["Durand Plomberie", "Téléphone : 06 11 22 33 44"]
    assert "SIREN" not in _all_text(notice)


def test_a_french_demo_is_published_by_the_user_who_prepared_it_and_its_visits_are_measured() -> None:
    notice = _notice(
        "FR",
        BusinessLegalIdentity(name="Barbier du Port", email="contact@barbier.example", legal_id="123 456 789"),
        is_demo=True,
        template_id="barber",
    )

    legal = _section(notice, 0)
    privacy = _section(notice, 1)
    text = _all_text(notice)
    assert notice.demo_notice == (
        "Ce site est une démonstration préparée par Atelier Web Durand pour Barbier du Port. Tant que Barbier du "
        "Port ne l'a pas mis en ligne à son nom, Atelier Web Durand en est l'éditeur et le responsable des données "
        "décrites ci-dessous."
    )
    assert _headings(legal) == [
        "Éditeur de la démonstration",
        "Directeur de la publication",
        "Entreprise présentée",
        "Hébergeur",
    ]
    assert _rendered(_block(legal, "Directeur de la publication")) == ["Alexis Durand"]
    assert "SIREN : 123 456 789" in _rendered(_block(legal, "Entreprise présentée"))
    assert _headings(privacy)[:4] == [
        "Responsable du traitement pendant la démonstration",
        "Mesure des visites de la démonstration",
        "Message laissé sur la démonstration",
        "Formulaire de contact",
    ]
    assert "PostHog" in text
    assert "y compris s'il est refermé sans être envoyé" in text
    assert "Atelier Web Durand ne reçoit pas ces e‑mails." in text
    assert "Google Maps" in text
    assert "Ce site ne mesure pas son audience" not in text


def test_a_swiss_delivered_site_has_an_impressum_and_follows_the_swiss_act() -> None:
    notice = _notice(
        "CH",
        BusinessLegalIdentity(
            name="Garage du Rhône Sàrl",
            address="Rue du Rhône 12, 1204 Genève",
            phone="022 123 45 67",
            email="info@garage-rhone.example",
            legal_id="CHE-123.456.789",
            vat_number="CHE-123.456.789 TVA",
        ),
        is_demo=False,
        template_id="mechanic-pitlane",
    )

    legal = _section(notice, 0)
    text = _all_text(notice)
    assert notice.locale == "fr-CH"
    assert notice.page_title == "Impressum et protection des données"
    assert [link.label for link in notice.links] == ["Impressum", "Protection des données"]
    assert _headings(legal) == ["Éditeur du site"]
    assert "IDE : CHE-123.456.789" in _rendered(_block(legal, "Éditeur du site"))
    assert "TVA : CHE-123.456.789 TVA" in _rendered(_block(legal, "Éditeur du site"))
    assert "RGPD" not in text
    assert "Vercel, Google et Cloudflare sont certifiés selon le Swiss-US Data Privacy Framework" in text
    assert "Préposé fédéral à la protection des données et à la transparence (PFPDT)" in text
    assert "Auto Ways" in text


def test_a_swiss_demo_still_follows_french_law_for_its_publisher() -> None:
    notice = _notice("CH", BusinessLegalIdentity(name="Garage du Rhône Sàrl"), is_demo=True)

    legal = _section(notice, 0)
    assert _headings(legal) == [
        "Éditeur de la démonstration",
        "Directeur de la publication",
        "Entreprise présentée",
        "Hébergeur",
    ]
    assert "Commission nationale de l'informatique et des libertés (CNIL)" in _all_text(notice)
    assert "IDE" not in _all_text(notice)


def test_a_belgian_site_names_its_enterprise_number_and_its_authority() -> None:
    notice = _notice(
        "BE",
        BusinessLegalIdentity(name="Plomberie Janssens SRL", legal_id="0123.456.789", vat_number="BE0123456789"),
        is_demo=False,
    )

    legal = _section(notice, 0)
    assert notice.locale == "fr-BE"
    assert _headings(legal) == ["Éditeur du site"]
    assert _rendered(_block(legal, "Éditeur du site")) == [
        "Plomberie Janssens SRL",
        "Numéro d'entreprise : 0123.456.789",
        "TVA : BE0123456789",
    ]
    assert "Autorité de protection des données (APD)" in _all_text(notice)


def test_a_belgian_site_without_enterprise_number_leaves_the_line_out() -> None:
    notice = _notice("BE", BusinessLegalIdentity(name="Plomberie Janssens"), is_demo=False)

    assert "Numéro d'entreprise" not in _all_text(notice)


def test_a_luxembourg_site_names_its_register_number_and_its_authority() -> None:
    notice = _notice("LU", BusinessLegalIdentity(name="Toitures Weber Sàrl", legal_id="B123456"), is_demo=False)

    assert notice.locale == "fr-LU"
    assert "RCS Luxembourg : B123456" in _rendered(_block(_section(notice, 0), "Éditeur du site"))
    assert "Commission nationale pour la protection des données (CNPD)" in _all_text(notice)


def test_a_luxembourg_demo_without_register_number_shows_none() -> None:
    notice = _notice("LU", BusinessLegalIdentity(name="Toitures Weber"), is_demo=True)

    assert "RCS Luxembourg" not in _all_text(notice)


def test_a_quebec_site_links_its_privacy_policy_and_names_the_person_in_charge() -> None:
    notice = _notice(
        "CA",
        BusinessLegalIdentity(
            name="Électricité Tremblay inc.",
            address="123, rue Sainte-Catherine Ouest, Montréal (Québec) H3B 1A1",
            phone="514 555-0199",
            email="info@tremblay.example",
            legal_id="1171234567",
            professional_license_label="Licence RBQ",
            professional_license_number="5678-1234-01",
        ),
        is_demo=False,
        template_id="landscaper-verdure",
    )

    legal = _section(notice, 0)
    privacy = _section(notice, 1)
    text = _all_text(notice)
    assert notice.locale == "fr-CA"
    assert [(link.label, link.anchor) for link in notice.links] == [
        ("Politique de confidentialité", "politique-de-confidentialite")
    ]
    assert legal.title == "Renseignements sur l'entreprise"
    assert _rendered(_block(legal, "Entreprise"))[-2:] == ["NEQ : 1171234567", "Licence RBQ : 5678-1234-01"]
    officer = _block(privacy, "Responsable de la protection des renseignements personnels")
    assert "Fonction : personne ayant la plus haute autorité au sein de l'entreprise" in _rendered(officer)
    assert "Courriel : info@tremblay.example" in _rendered(officer)
    assert "vous consentez à ce que Électricité Tremblay inc. utilise ces renseignements" in text
    assert "Communication à l'extérieur du Québec" in _headings(privacy)
    assert "Commission d'accès à l'information du Québec" in text
    assert "e-mail" not in text.lower()
    assert "e‑mail" not in text.lower()
    assert "RGPD" not in text


def test_a_quebec_demo_without_neq_still_shows_its_rbq_licence() -> None:
    notice = _notice(
        "CA",
        BusinessLegalIdentity(
            name="Toitures Gagnon",
            professional_license_label="Licence RBQ",
            professional_license_number="5678-1234-01",
        ),
        is_demo=True,
    )

    presented = _rendered(_block(_section(notice, 0), "Entreprise présentée"))
    assert presented == ["Toitures Gagnon", "Licence RBQ : 5678-1234-01"]
    assert "NEQ" not in _all_text(notice)


def test_a_business_name_is_never_rewritten_in_regional_words() -> None:
    notice = _notice("CA", BusinessLegalIdentity(name="Mail Express"), is_demo=False)

    assert "adressé à Mail Express" in _all_text(notice)


def test_a_name_ending_a_sentence_on_its_own_period_gets_no_second_one() -> None:
    text = _all_text(_notice("CA", BusinessLegalIdentity(name="Toitures Gagnon inc."), is_demo=False))

    assert "adressé à Toitures Gagnon inc. Rien ne part" in text
    assert "inc.." not in text


def test_the_privacy_policy_lists_only_the_flows_the_template_really_has() -> None:
    without_form = _all_text(
        _notice("FR", BusinessLegalIdentity(name="Atelier Morel"), is_demo=False, template_id="artisan-edito")
    )
    garage = _all_text(
        _notice("FR", BusinessLegalIdentity(name="Garage Morel"), is_demo=False, template_id="mechanic-pitlane")
    )

    assert "Ce site n'a pas de formulaire." in without_form
    assert "Google Maps" not in without_form
    assert "Auto Ways" not in without_form
    assert "Google Fonts" in without_form
    assert "Google Maps" in garage
    assert "Auto Ways" in garage


def _user(db: Session) -> User:
    user = User(
        name="Alexis Durand",
        email="login@atelier-web.example",
        hashed_password="x",
        company_name="Atelier Web Durand",
        contact_email="contact@atelier-web.example",
        postal_address="4 rue des Lilas, 35000 Rennes",
    )
    db.add(user)
    db.commit()
    return user


def _prospect(
    db: Session,
    user: User,
    *,
    country: str = "FR",
    address: str | None = "8 rue de Brest, 35000 Rennes",
    city: str | None = "Rennes",
) -> ProspectDB:
    prospect = ProspectDB(
        name="Durand Plomberie",
        address=address,
        city=city,
        country=country,
        phone="0611223344",
        email="contact@durand.example",
        category="Plombier",
        source="google",
        confidence=3,
        user_id=user.id,
    )
    db.add(prospect)
    db.commit()
    return prospect


def _site(db: Session, user: User, prospect: ProspectDB, *, status: DemoSiteStatus) -> DemoSite:
    site = DemoSite(
        user_id=user.id,
        prospect_id=prospect.id,
        slug="durand-plomberie",
        template_id="plumber-signature",
        business_name="Durand Plomberie",
        phone="0611223344",
        email="contact@durand.example",
        status=status.value,
        content_json={"businessName": "Durand Plomberie", "phone": "06 11 22 33 44", "palette": {"accent": "#e4572e"}},
        expires_at=datetime.now(UTC) + timedelta(days=21),
    )
    db.add(site)
    db.commit()
    return site


def test_a_delivered_site_reads_its_sale_and_its_trusted_decision_maker(db: Session) -> None:
    user = _user(db)
    prospect = _prospect(db, user)
    site = _site(db, user, prospect, status=DemoSiteStatus.DELIVERED)
    db.add(
        ProspectEnrichment(
            prospect_id=prospect.id,
            user_id=user.id,
            contact_first_name="Alexis",
            contact_last_name="Durand",
            contact_name_status=ContactNameStatus.AUTO.value,
            contact_siren="987654321",
        )
    )
    db.add(
        Order(
            user_id=user.id,
            prospect_id=prospect.id,
            demo_site_id=site.id,
            status=OrderStatus.DELIVERED.value,
            business_name="SARL Plomberie Durand",
            billing_tax_id="12345678900012",
            billing_vat_number="FR32123456789",
        )
    )
    db.commit()

    sources = SiteLegalSourceLoader.load(db, site, site.content_json)

    assert sources.is_demo is False
    assert sources.publisher is None
    assert sources.business.name == "SARL Plomberie Durand"
    assert sources.business.trade_name == "Durand Plomberie"
    assert sources.business.legal_id == "12345678900012"
    assert sources.business.vat_number == "FR32123456789"
    assert sources.business.publication_director == "Alexis Durand"
    assert sources.business.address == "8 rue de Brest, 35000 Rennes"
    assert sources.accent_color == "#e4572e"


def test_a_demo_never_publishes_the_siren_of_a_decision_maker_still_to_confirm(db: Session) -> None:
    user = _user(db)
    prospect = _prospect(db, user)
    site = _site(db, user, prospect, status=DemoSiteStatus.ACTIVE)
    db.add(
        ProspectEnrichment(
            prospect_id=prospect.id,
            user_id=user.id,
            proposed_first_name="Alexis",
            proposed_last_name="Durand",
            proposed_state=ProposedContactState.PENDING.value,
            contact_siren="987654321",
        )
    )
    db.commit()

    sources = SiteLegalSourceLoader.load(db, site, site.content_json)

    assert sources.is_demo is True
    assert sources.business.legal_id is None
    assert sources.publisher is not None
    assert sources.publisher.label == "Atelier Web Durand"
    assert sources.publisher.email == "contact@atelier-web.example"


def test_a_street_only_address_gets_its_postal_code_and_its_town(db: Session) -> None:
    user = _user(db)
    prospect = _prospect(db, user, address="250 rue du Truel", city="Montpellier")
    site = _site(db, user, prospect, status=DemoSiteStatus.ACTIVE)
    db.add(ProspectEnrichment(prospect_id=prospect.id, user_id=user.id, place_postal_code="34090"))
    db.commit()

    sources = SiteLegalSourceLoader.load(db, site, site.content_json)

    assert sources.business.address == "250 rue du Truel, 34090 Montpellier"


def test_a_quebec_address_writes_the_town_before_the_postal_code(db: Session) -> None:
    user = _user(db)
    prospect = _prospect(db, user, country="CA", address="1200, boulevard Saint-Martin Ouest", city="Laval")
    site = _site(db, user, prospect, status=DemoSiteStatus.ACTIVE)
    db.add(ProspectEnrichment(prospect_id=prospect.id, user_id=user.id, place_postal_code="H7S 2E4"))
    db.commit()

    sources = SiteLegalSourceLoader.load(db, site, site.content_json)

    assert sources.business.address == "1200, boulevard Saint-Martin Ouest, Laval H7S 2E4"


def test_a_delivered_site_without_public_address_shows_its_billing_address(db: Session) -> None:
    user = _user(db)
    prospect = _prospect(db, user, address=None, city=None)
    site = _site(db, user, prospect, status=DemoSiteStatus.DELIVERED)
    db.add(
        Order(
            user_id=user.id,
            prospect_id=prospect.id,
            demo_site_id=site.id,
            status=OrderStatus.PAID.value,
            business_name="Durand Plomberie",
            billing_address="3 impasse des Ajoncs",
            billing_zip_code="35700",
            billing_city="Rennes",
        )
    )
    db.commit()

    delivered = SiteLegalSourceLoader.load(db, site, site.content_json)
    site.status = DemoSiteStatus.ACTIVE.value
    demo = SiteLegalSourceLoader.load(db, site, site.content_json)

    assert delivered.business.address == "3 impasse des Ajoncs, 35700 Rennes"
    assert demo.business.address is None


def test_an_emptied_storyblok_field_falls_back_on_the_records(db: Session) -> None:
    user = _user(db)
    prospect = _prospect(db, user)
    site = _site(db, user, prospect, status=DemoSiteStatus.DELIVERED)

    edited = SiteLegalSourceLoader.load(db, site, {"businessName": "Durand Plomberie", "phone": "07 98 76 54 32"})
    emptied = SiteLegalSourceLoader.load(db, site, {"businessName": "", "phone": "", "email": ""})

    assert edited.business.phone == "07 98 76 54 32"
    assert emptied.business.name == "Durand Plomberie"
    assert emptied.business.phone == "06 11 22 33 44"
    assert emptied.business.email == "contact@durand.example"


def test_the_public_demo_payload_carries_the_legal_block(db: Session) -> None:
    user = _user(db)
    prospect = _prospect(db, user, country="CH")
    site = _site(db, user, prospect, status=DemoSiteStatus.ACTIVE)

    payload = asyncio.run(get_public_demo_site(site.slug, db))
    db.refresh(site)

    assert payload.legal is not None
    assert payload.legal.locale == "fr-CH"
    assert [link.label for link in payload.legal.links] == ["Impressum", "Protection des données"]
    assert payload.legal.demo_notice is not None
    assert "legal" not in (payload.content_json or {})
    assert "legal" not in site.content_json
