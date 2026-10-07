"""Rules of the prospect search that need no network: trades, identity, decision, Facebook results, judge answers."""

from typing import ClassVar

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from enums.prospect_search import (
    CandidateOrigin,
    CandidateRejectReason,
    CandidateStatus,
    EmailProofLevel,
    ProspectSearchChannel,
    ProspectSearchValidationMode,
)
from enums.website_status import WebsiteStatus
from models.email_log import EmailLog
from models.facebook_exclusion import FacebookPageExclusion
from models.prospect_db import ProspectDB
from models.prospect_search_candidate import ProspectSearchCandidate
from schemas.prospect_search import CandidateDecisions, ProspectSearchCreate
from services.prospect_search.business_name import BusinessName
from services.prospect_search.candidate_decision import CandidateDecision, SearchCriteria
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_identity import CandidateIdentity, KnownBusinessIndex
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.facebook_page_results import FacebookPageResults
from services.prospect_search.registry_sources import RegistryCompany
from services.prospect_search.search_judge import SearchJudge, SearchResultLine
from services.prospect_search.search_zones import SearchZones
from services.prospect_search.trade_catalog import TradeCatalog

USER_ID = 7
_EMAIL_ONLY = SearchCriteria(channel=ProspectSearchChannel.EMAIL, only_without_website=True, minimum_rating=None)
_LANDSCAPER = TradeCatalog.resolve("paysagiste")


def _facts(**overrides: object) -> CandidateFacts:
    """A verified Swiss landscaper with nothing against it and no contact yet."""
    values: dict[str, object] = {
        "name": "Tendance Nature",
        "trade_key": "paysagiste",
        "country": "CH",
        "origin": CandidateOrigin.GOOGLE_LOCAL.value,
        "city": "Sion",
        "google_category": "Paysagiste",
        "is_verified": True,
    }
    values.update(overrides)
    return CandidateFacts(**values)  # type: ignore[arg-type]


class TestTradeCatalog:
    def test_an_accented_trade_resolves_to_its_profile(self) -> None:
        assert TradeCatalog.resolve("Électricien").key == "electricien"

    def test_the_swiss_wording_of_plumbing_resolves_to_the_plumber_profile(self) -> None:
        profile = TradeCatalog.resolve("sanitaire-chauffage")

        assert profile.key == "plombier"
        assert profile.terms_for("CH")[0] == "installateur sanitaire"
        assert profile.terms_for("FR")[0] == "plombier chauffagiste"

    def test_an_unknown_trade_is_searched_with_the_typed_words(self) -> None:
        profile = TradeCatalog.resolve("Serrurier")

        assert profile.is_generic is True
        assert profile.terms_for("FR") == ("Serrurier",)
        assert profile.prospect_category == "serrurier"

    def test_the_electrician_registry_domains_leave_out_the_heating_trades(self) -> None:
        assert TradeCatalog.resolve("électricien").rge_domains == ("Radiateurs électriques, dont régulation.",)

    def test_a_power_plant_or_a_substation_is_not_an_electrician(self) -> None:
        electrician = TradeCatalog.resolve("électricien")

        assert electrician.accepts_category("Centrale hydroélectrique") is False
        assert electrician.accepts_category("Sous-station électrique") is False
        assert electrician.accepts_category("Électricien") is True
        assert electrician.accepts_category("Entrepreneur en électricité") is True

    @pytest.mark.parametrize(
        ("trade", "category", "expected"),
        [
            ("garage", "Concessionnaire automobile", True),
            ("garage", "Carrosserie", True),
            ("garage", "Service de réparation de jantes", True),
            ("garage", "Vendeur de voitures d'occasion", True),
            ("garage", "Service de remorquage", True),
            ("garage", "Agence d'assurance automobile", False),
            ("garage", "Location de voitures", False),
            ("garage", "Borne de recharge pour véhicules électriques", False),
            ("paysagiste", "Entreprise de clôtures", True),
            ("paysagiste", "Entrepreneur en systèmes d'irrigation", True),
            ("paysagiste", "Service de débroussaillage", True),
            ("paysagiste", "Jardin d'enfants", False),
            ("paysagiste", "Jardin botanique", False),
            ("électricien", "Entreprise de domotique", True),
            ("électricien", "Borne de recharge pour véhicules électriques", False),
            ("électricien", "Service de réparation d'appareils électriques", False),
        ],
    )
    def test_a_trade_covers_the_whole_theme_of_its_site_template(
        self, trade: str, category: str, expected: bool
    ) -> None:
        assert TradeCatalog.resolve(trade).accepts_category(category) is expected

    def test_a_garage_door_supplier_is_not_a_garage(self) -> None:
        garage = TradeCatalog.resolve("garage")

        assert garage.accepts_category("Fournisseur de portes de garage") is False
        assert garage.accepts_category("Garage door supplier") is False
        assert garage.accepts_category("Atelier de réparation automobile") is True

    def test_a_hospital_keeping_an_electrical_licence_is_no_tradesperson(self) -> None:
        assert (
            RegistryCompany.is_institution("Hôpital Ste-Croix", "contact@ssss.gouv.qc.ca", city="Drummondville") is True
        )
        assert (
            RegistryCompany.is_institution(
                "Ouellet Électrique inc.", "ouelletelectrique@hotmail.ca", city="Trois-Rivières"
            )
            is False
        )

    def test_a_shop_category_is_not_the_trade(self) -> None:
        assert _LANDSCAPER.accepts_category("Paysagiste") is True
        assert _LANDSCAPER.accepts_category("Magasin d'articles pour l'aménagement paysager") is False
        assert _LANDSCAPER.accepts_category(None) is True


class TestSearchZones:
    def test_asked_towns_are_searched_alone_and_in_order(self) -> None:
        plan = SearchZones.plan(country="CH", asked_cities=[" Sion ", "Bulle"], already_scanned=set(), seed=1)

        assert plan == ["Sion", "Bulle"]

    def test_towns_already_scanned_for_the_trade_come_last(self) -> None:
        plan = SearchZones.plan(country="CH", asked_cities=[], already_scanned={"sion", "geneve"}, seed=3)

        assert set(plan[-2:]) == {"Sion", "Genève"}
        assert len(plan) == len(SearchZones.towns_of("CH"))

    def test_brittany_is_left_out_of_the_french_towns(self) -> None:
        assert not {"Rennes", "Brest", "Quimper", "Vannes", "Saint-Brieuc", "Lorient"} & set(SearchZones.towns_of("FR"))


class TestCandidateIdentity:
    def test_the_same_phone_written_two_ways_gives_one_key(self) -> None:
        assert CandidateIdentity.phone_key("079 473 19 61", "CH") == CandidateIdentity.phone_key("+41794731961", "CH")

    def test_a_facebook_page_is_one_key_whatever_the_sub_page(self) -> None:
        root = CandidateIdentity.facebook_key("https://www.facebook.com/filvertsarl/?locale=fr_FR")

        assert root == CandidateIdentity.facebook_key("https://m.facebook.com/filvertsarl/about")
        assert CandidateIdentity.facebook_key("https://www.facebook.com/groups/123/posts/456") is None

    def test_word_order_legal_form_and_accents_do_not_change_the_name_key(self) -> None:
        assert CandidateIdentity.name_key("Garage Dupont SARL", "Sion") == CandidateIdentity.name_key(
            "Dupont Garage", "sion"
        )

    def test_a_facebook_page_is_one_key_under_its_people_and_profile_addresses(self) -> None:
        people = CandidateIdentity.facebook_key("https://www.facebook.com/people/Jardins-Martin/100075901827931/")

        assert people == CandidateIdentity.facebook_key("https://www.facebook.com/profile.php?id=100075901827931")
        assert people == CandidateIdentity.facebook_key("https://www.facebook.com/p/Jardins-Martin-100075901827931/")

    def test_the_google_identifier_is_read_from_both_maps_url_forms(self) -> None:
        cid = str(int("66d92e58019e9a3e", 16))

        assert CandidateIdentity.cid_of_maps_url(f"https://www.google.com/maps?cid={cid}") == cid
        assert (
            CandidateIdentity.cid_of_maps_url(
                "https://www.google.com/maps/place/X/data=!4m2!3m1!1s0x478edc8a846f513d:0x66d92e58019e9a3e"
            )
            == cid
        )


class TestKnownBusinessIndex:
    def _prospect(self, db: Session, **overrides: object) -> ProspectDB:
        values: dict[str, object] = {
            "name": "Filvert Sarl",
            "city": "Sion",
            "country": "CH",
            "phone": "079 473 19 61",
            "category": "paysagiste",
            "source": "manual",
            "confidence": 3,
            "user_id": USER_ID,
        }
        values.update(overrides)
        prospect = ProspectDB(**values)
        db.add(prospect)
        db.commit()
        return prospect

    def _keys(self, **overrides: object) -> list[str]:
        values: dict[str, object] = {"name": "Autre nom", "city": "Bulle", "country": "CH"}
        values.update(overrides)
        return CandidateIdentity.keys(**values)  # type: ignore[arg-type]

    def test_a_prospect_is_recognised_by_its_phone_under_another_name(self, db: Session) -> None:
        prospect = self._prospect(db)
        index = KnownBusinessIndex.load(db, user_id=USER_ID, organization_id=None, search_id=1)

        known = index.match(self._keys(phone="+41 79 473 19 61"))

        assert known is not None
        assert (known.reason, known.prospect_id) == (CandidateRejectReason.ALREADY_KNOWN, prospect.id)

    def test_a_do_not_contact_prospect_is_reported_as_such(self, db: Session) -> None:
        self._prospect(db, do_not_contact=True, email="refus@example.com")
        index = KnownBusinessIndex.load(db, user_id=USER_ID, organization_id=None, search_id=1)

        match = index.match(self._keys(email="refus@example.com"))

        assert match is not None and match.reason is CandidateRejectReason.DO_NOT_CONTACT

    def test_another_user_s_prospect_is_not_known(self, db: Session) -> None:
        self._prospect(db, user_id=USER_ID + 1)
        index = KnownBusinessIndex.load(db, user_id=USER_ID, organization_id=None, search_id=1)

        assert index.match(self._keys(phone="079 473 19 61")) is None

    def test_a_business_an_earlier_search_discarded_for_its_website_is_remembered(self, db: Session) -> None:
        db.add(
            ProspectSearchCandidate(
                search_id=1,
                user_id=USER_ID,
                trade="paysagiste",
                origin=CandidateOrigin.GOOGLE_LOCAL.value,
                name="Filvert Sarl",
                country="CH",
                status=CandidateStatus.REJECTED.value,
                reject_reason=CandidateRejectReason.HAS_WEBSITE.value,
                identity_keys=["tel:+41794731961", "name:filvert|sion"],
                evidence=[],
            )
        )
        db.commit()

        later_search = KnownBusinessIndex.load(db, user_id=USER_ID, organization_id=None, search_id=2)
        same_search = KnownBusinessIndex.load(db, user_id=USER_ID, organization_id=None, search_id=1)

        remembered = later_search.match(["tel:+41794731961"])

        assert remembered is not None and remembered.reason is CandidateRejectReason.PREVIOUSLY_REJECTED
        assert same_search.match(["tel:+41794731961"]) is None

    def test_a_second_listing_of_a_business_the_run_proposed_is_not_proposed_again(self) -> None:
        index = KnownBusinessIndex()
        index.remember_proposed(["tel:+41790000012", "name:ducret paysagiste|servion"])

        second_listing = index.match(["tel:+41790000012", "name:ducret paysagiste|jongny"])

        assert second_listing is not None and second_listing.reason is CandidateRejectReason.AWAITING_DECISION
        assert index.match(["name:ducret paysagiste|servion"]) is None

    def test_a_second_listing_of_a_business_the_run_discarded_for_good_is_discarded_too(self) -> None:
        index = KnownBusinessIndex()
        index.remember_rejected(
            ["tel:+41790000041", "name:jardins rochat|sion"], CandidateRejectReason.NO_ADVERTISING.value
        )
        index.remember_rejected(["tel:+41790000042"], CandidateRejectReason.NO_CONTACT.value)

        second_listing = index.match(["cid:3475807440485315643", "tel:+41790000041"])

        assert second_listing is not None and second_listing.reason is CandidateRejectReason.PREVIOUSLY_REJECTED
        assert second_listing.detail == "Déjà écarté par cette recherche sous une autre fiche."
        assert index.match(["tel:+41790000042"]) is None

    def test_what_the_run_proposed_and_discarded_survives_the_reload_before_a_town(self, db: Session) -> None:
        index = KnownBusinessIndex.load(db, user_id=USER_ID, organization_id=None, search_id=1)
        index.remember_proposed(["tel:+41790000043"])
        index.remember_rejected(["tel:+41790000044"], CandidateRejectReason.HAS_WEBSITE.value)

        reloaded = KnownBusinessIndex.load(db, user_id=USER_ID, organization_id=None, search_id=1)
        reloaded.take_run_memory_from(index)

        assert reloaded.match(["tel:+41790000043"]) is not None
        assert reloaded.match(["tel:+41790000044"]) is not None

    def test_a_business_awaiting_validation_is_not_proposed_again_by_a_later_search(self, db: Session) -> None:
        db.add(
            ProspectSearchCandidate(
                search_id=1,
                user_id=USER_ID,
                trade="paysagiste",
                origin=CandidateOrigin.GOOGLE_LOCAL.value,
                name="Tendance Nature",
                country="CH",
                status=CandidateStatus.KEPT.value,
                identity_keys=["tel:+41787575742", "name:nature tendance|sion"],
                evidence=[],
            )
        )
        db.commit()

        later_search = KnownBusinessIndex.load(db, user_id=USER_ID, organization_id=None, search_id=2)
        same_search = KnownBusinessIndex.load(db, user_id=USER_ID, organization_id=None, search_id=1)

        known = later_search.match(["tel:+41787575742"])
        assert known is not None
        assert (known.reason, known.prospect_id) == (CandidateRejectReason.AWAITING_DECISION, None)
        assert same_search.match(["tel:+41787575742"]) is None

    def test_an_address_already_written_to_is_known_even_without_its_prospect(self, db: Session) -> None:
        db.add(
            EmailLog(
                user_id=USER_ID,
                recipient_email="Deja.Contacte@gmail.com",
                subject="Votre site",
                body_html="<p>Bonjour</p>",
                provider="resend",
            )
        )
        db.commit()
        index = KnownBusinessIndex.load(db, user_id=USER_ID, organization_id=None, search_id=1)

        known = index.match(self._keys(email="deja.contacte@gmail.com"))

        assert known is not None
        assert (known.reason, known.prospect_id) == (CandidateRejectReason.ALREADY_KNOWN, None)
        assert "email" in known.detail

    def test_a_page_the_former_facebook_search_discarded_for_its_website_stays_discarded(self, db: Session) -> None:
        db.add(
            FacebookPageExclusion(
                user_id=USER_ID, page_url="https://www.facebook.com/filvertsarl", reason="has_website"
            )
        )
        db.add(FacebookPageExclusion(user_id=USER_ID, page_url="https://www.facebook.com/sansemail", reason="no_email"))
        db.commit()
        index = KnownBusinessIndex.load(db, user_id=USER_ID, organization_id=None, search_id=1)

        discarded = index.match(self._keys(facebook_url="https://m.facebook.com/filvertsarl/about"))

        assert discarded is not None and discarded.reason is CandidateRejectReason.PREVIOUSLY_REJECTED
        assert index.match(self._keys(facebook_url="https://www.facebook.com/sansemail")) is None


class TestCandidateDecision:
    def test_a_proven_email_meets_the_email_objective(self) -> None:
        facts = _facts(email="contact@tendance.ch", email_proof_level=EmailProofLevel.PUBLISHED.value)

        assert CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY).status is CandidateStatus.KEPT

    def test_a_mobile_without_email_is_set_aside_not_discarded(self) -> None:
        verdict = CandidateDecision.decide(_facts(phone="078 757 57 42"), _LANDSCAPER, _EMAIL_ONLY)

        assert (verdict.status, verdict.detail) == (
            CandidateStatus.SET_ASIDE,
            "Portable sans email : joignable par SMS.",
        )

    def test_an_email_without_mobile_is_set_aside_by_a_search_for_sms(self) -> None:
        sms_only = SearchCriteria(channel=ProspectSearchChannel.SMS, only_without_website=True, minimum_rating=None)
        facts = _facts(email="contact@tendance.ch", email_proof_level=EmailProofLevel.PUBLISHED.value)

        verdict = CandidateDecision.decide(facts, _LANDSCAPER, sms_only)

        assert (verdict.status, verdict.detail) == (
            CandidateStatus.SET_ASIDE,
            "Email sans portable : joignable par email.",
        )

    def test_a_guessed_email_waits_for_the_user(self) -> None:
        facts = _facts(email="peutetre@gmail.com", email_proof_level=EmailProofLevel.GUESSED.value)

        assert CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY).status is CandidateStatus.TO_CONFIRM

    def test_an_unread_facebook_page_is_read_before_giving_up_on_the_email(self) -> None:
        facts = _facts(phone="078 757 57 42", facebook_url="https://www.facebook.com/tendance")

        assert CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY).status is CandidateStatus.NEEDS_BROWSER

        facts.is_facebook_page_read = True
        assert CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY).status is CandidateStatus.SET_ASIDE

    def test_no_email_and_a_landline_is_discarded_for_lack_of_contact(self) -> None:
        verdict = CandidateDecision.decide(_facts(phone="027 203 13 88"), _LANDSCAPER, _EMAIL_ONLY)

        assert verdict.reject_reason is CandidateRejectReason.NO_CONTACT

    def test_a_working_website_discards_and_a_dead_one_does_not(self) -> None:
        proven = {"email": "contact@tendance.ch", "email_proof_level": EmailProofLevel.DIRECTORY.value}
        live = _facts(website="https://tendance.ch", website_status=WebsiteStatus.LIVE.value, **proven)
        dead = _facts(website="https://tendance.ch", website_status=WebsiteStatus.DEAD.value, **proven)

        assert (
            CandidateDecision.decide(live, _LANDSCAPER, _EMAIL_ONLY).reject_reason is CandidateRejectReason.HAS_WEBSITE
        )
        assert CandidateDecision.decide(dead, _LANDSCAPER, _EMAIL_ONLY).status is CandidateStatus.KEPT

    def test_a_website_declared_on_the_listing_but_not_found_is_left_to_the_user(self) -> None:
        proven = {"email": "contact@tendance.ch", "email_proof_level": EmailProofLevel.DIRECTORY.value}
        untraced = _facts(has_website_button=True, **proven)
        declared_as_facebook_page = _facts(
            has_website_button=True, facebook_url="https://www.facebook.com/tendance", **proven
        )

        verdict = CandidateDecision.decide(untraced, _LANDSCAPER, _EMAIL_ONLY)

        assert verdict.status is CandidateStatus.TO_CONFIRM
        assert "déclaré sur sa fiche Google" in (verdict.detail or "")
        assert (
            CandidateDecision.decide(declared_as_facebook_page, _LANDSCAPER, _EMAIL_ONLY).status is CandidateStatus.KEPT
        )

    def test_a_search_open_to_businesses_with_a_website_keeps_them(self) -> None:
        criteria = SearchCriteria(channel=ProspectSearchChannel.EMAIL, only_without_website=False, minimum_rating=None)
        facts = _facts(
            website="https://tendance.ch",
            website_status=WebsiteStatus.LIVE.value,
            email="contact@tendance.ch",
            email_proof_level=EmailProofLevel.DIRECTORY.value,
        )

        assert CandidateDecision.decide(facts, _LANDSCAPER, criteria).status is CandidateStatus.KEPT

    def test_the_two_channel_objective_wants_both_and_sets_aside_a_single_one(self) -> None:
        criteria = SearchCriteria(
            channel=ProspectSearchChannel.EMAIL_AND_SMS, only_without_website=True, minimum_rating=None
        )
        proven = {"email": "contact@tendance.ch", "email_proof_level": EmailProofLevel.PUBLISHED.value}

        assert CandidateDecision.decide(_facts(phone="078 757 57 42", **proven), _LANDSCAPER, criteria).status is (
            CandidateStatus.KEPT
        )
        assert CandidateDecision.decide(_facts(phone="027 203 13 88", **proven), _LANDSCAPER, criteria).status is (
            CandidateStatus.SET_ASIDE
        )

    def test_closed_chain_and_wrong_trade_are_discarded_with_their_reason(self) -> None:
        assert (
            CandidateDecision.decide(_facts(is_closed=True), _LANDSCAPER, _EMAIL_ONLY).reject_reason
            is CandidateRejectReason.CLOSED
        )
        assert (
            CandidateDecision.decide(_facts(is_chain=True), _LANDSCAPER, _EMAIL_ONLY).reject_reason
            is CandidateRejectReason.CHAIN
        )
        assert (
            CandidateDecision.decide(_facts(google_category="Fleuriste"), _LANDSCAPER, _EMAIL_ONLY).reject_reason
            is CandidateRejectReason.WRONG_TRADE
        )

    def test_a_low_rating_only_counts_once_enough_reviews_back_it(self) -> None:
        criteria = SearchCriteria(channel=ProspectSearchChannel.SMS, only_without_website=True, minimum_rating=4.0)
        few_reviews = _facts(phone="078 757 57 42", google_rating=3.0, google_reviews_count=2)
        many_reviews = _facts(phone="078 757 57 42", google_rating=3.0, google_reviews_count=40)

        assert CandidateDecision.decide(few_reviews, _LANDSCAPER, criteria).status is CandidateStatus.KEPT
        assert CandidateDecision.decide(many_reviews, _LANDSCAPER, criteria).reject_reason is (
            CandidateRejectReason.LOW_RATING
        )

    def test_an_unverified_candidate_is_never_kept_on_its_own(self) -> None:
        facts = _facts(
            is_verified=False, email="contact@tendance.ch", email_proof_level=EmailProofLevel.PUBLISHED.value
        )

        assert CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY).status is CandidateStatus.TO_CONFIRM

    def test_a_better_proven_email_replaces_a_weaker_one_never_the_reverse(self) -> None:
        facts = _facts()

        assert facts.offer_email("guess@gmail.com", EmailProofLevel.GUESSED, source="recherche") is True
        assert facts.offer_email("page@gmail.com", EmailProofLevel.PUBLISHED, source="Page Facebook") is True
        assert facts.offer_email("annuaire@gmail.com", EmailProofLevel.DIRECTORY, source="annuaire") is False
        assert facts.email == "page@gmail.com"

    def test_a_listing_whose_address_is_in_another_country_is_discarded(self) -> None:
        facts = _facts(
            address="6 Rue des Vignes, 88700 Romont, France",
            email="electricitemazza@outlook.fr",
            email_proof_level=EmailProofLevel.PUBLISHED.value,
        )

        assert CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY).reject_reason is (
            CandidateRejectReason.OUT_OF_COUNTRY
        )

    def test_a_facebook_page_without_a_phone_is_left_to_the_user(self) -> None:
        facts = _facts(
            name="Jardins Rochat",
            origin=CandidateOrigin.FACEBOOK_SEARCH.value,
            city=None,
            searched_city="Martigny",
            facebook_url="https://www.facebook.com/electric.vs",
            is_facebook_page_read=True,
            email="willkommen@elektroverband-oberwallis.ch",
            email_proof_level=EmailProofLevel.PUBLISHED.value,
        )

        assert CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY).status is CandidateStatus.TO_CONFIRM

        facts.phone = "079 000 00 11"
        assert CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY).status is CandidateStatus.KEPT

    def test_a_facebook_page_whose_name_does_not_say_the_trade_is_left_to_the_user(self) -> None:
        facts = _facts(
            name="Ici Exemple & Région : nos commerces, notre force",
            google_category=None,
            origin=CandidateOrigin.FACEBOOK_SEARCH.value,
            phone="078 000 00 81",
            email="commerces.exemple@gmail.com",
            email_proof_level=EmailProofLevel.PUBLISHED.value,
        )
        electrician = TradeCatalog.resolve("électricien")

        assert CandidateDecision.decide(facts, electrician, _EMAIL_ONLY).status is CandidateStatus.TO_CONFIRM

        facts.name = "Rochat Électricité"
        assert CandidateDecision.decide(facts, electrician, _EMAIL_ONLY).status is CandidateStatus.KEPT


class TestBusinessNaming:
    def test_a_name_sharing_only_generic_words_is_another_business(self) -> None:
        facts = CandidateFacts(
            name="Garage du Soleil", trade_key="garage", country="CH", origin="google_local", city="Ardon"
        )
        garage = TradeCatalog.resolve("garage")

        assert CandidateVerifier.names_business("Garage du Moulin SA - Ardon", facts, garage) is False
        assert CandidateVerifier.names_business("Garage du Soleil, Yves Rochat - Ardon", facts, garage) is True
        assert CandidateVerifier.names_business("Garage du Lac SA", facts, garage) is False


class TestFacebookPageResults:
    def _line(self, link: str, title: str, description: str = "") -> SearchResultLine:
        return SearchResultLine(link=link, host="facebook.com", title=title, description=description)

    def test_only_the_root_of_a_page_placed_in_the_town_is_kept(self) -> None:
        pages = FacebookPageResults.business_pages(
            [
                self._line("https://www.facebook.com/jardinsdupont/", "Les Jardins Dupont | Bulle"),
                self._line("https://www.facebook.com/bulledejardin/", "Bulle de Jardin | Sainte-Savine"),
                self._line("https://www.facebook.com/prevert81/posts/123", "Bulle Chauliac paysagiste"),
                self._line("https://www.facebook.com/BNIGruyere/photos/456", "bni #gruyère #bulle # ..."),
                self._line(
                    "https://www.facebook.com/p/Paysages-Martin-100075901827931/",
                    "Paysages Martin",
                    "Paysagiste à Bulle, entretien de jardins.",
                ),
            ],
            town="Bulle",
        )

        assert [page.name for page in pages] == ["Les Jardins Dupont", "Paysages Martin"]
        assert pages[1].page_url == "https://www.facebook.com/100075901827931"

    def test_a_person_named_like_the_town_or_a_personal_profile_is_no_page_of_the_town(self) -> None:
        pages = FacebookPageResults.business_pages(
            [
                self._line("https://www.facebook.com/paul.rolle.10/", "Paul Rolle", "Paul Rolle, électricien."),
                self._line(
                    "https://www.facebook.com/jean.dupont.52/",
                    "Jean Dupont",
                    "Jean Dupont est sur Facebook. Inscrivez-vous sur Facebook pour communiquer avec Jean Dupont "
                    "et d'autres personnes que vous pouvez connaître. Rolle.",
                ),
                self._line(
                    "https://www.facebook.com/electriciterolle/",
                    "Electricité Paul Rolle",
                    "Electricité Paul Rolle, Route de Genève 1, 1180 Rolle.",
                ),
            ],
            town="Rolle",
        )

        assert [page.name for page in pages] == ["Electricité Paul Rolle"]


class TestSearchJudgeAnswer:
    _RESULTS: ClassVar[list[SearchResultLine]] = [
        SearchResultLine(
            link="https://www.moneyhouse.ch/fr/company/x",
            host="moneyhouse.ch",
            title="L'Art du Jardin, Mirco Ferro à Vevey",
            description="Inscription de Mirco Ferro. Contact : info@artdujardin.ch",
        ),
        SearchResultLine(link="https://annuaire.ch/y", host="annuaire.ch", title="Jardins", description="Autre fiche"),
    ]

    def test_a_name_and_an_email_written_in_the_result_are_kept(self) -> None:
        verdict = SearchJudge.parse_answer(
            {
                "own_website_index": None,
                "owner_name": "Mirco Ferro",
                "owner_name_index": 0,
                "emails": [{"email": "info@artdujardin.ch", "index": 0, "belongs_to_business": True}],
            },
            self._RESULTS,
        )

        assert verdict.owner_name == "Mirco Ferro"
        assert [(entry.email, entry.belongs_to_business) for entry in verdict.emails] == [("info@artdujardin.ch", True)]

    def test_what_is_not_written_in_the_pointed_result_is_dropped(self) -> None:
        verdict = SearchJudge.parse_answer(
            {
                "own_website_index": 9,
                "owner_name": "Jean Invente",
                "owner_name_index": 1,
                "emails": [{"email": "invente@gmail.com", "index": 1, "belongs_to_business": True}],
                "matches_trade": None,
            },
            self._RESULTS,
        )

        assert verdict.own_website_index is None
        assert verdict.owner_name is None
        assert verdict.emails == []
        assert verdict.matches_trade is True


def test_an_overlong_trade_or_town_is_refused_before_the_search_is_stored() -> None:
    assert ProspectSearchCreate(trades=["t" * 60], cities=["v" * 80]).trades == ["t" * 60]
    with pytest.raises(ValidationError):
        ProspectSearchCreate(trades=["t" * 61])
    with pytest.raises(ValidationError):
        ProspectSearchCreate(trades=["paysagiste"], cities=["v" * 81])


def test_a_search_waits_for_the_user_to_validate_unless_asked_otherwise() -> None:
    assert ProspectSearchCreate(trades=["paysagiste"]).validation_mode == ProspectSearchValidationMode.MANUAL
    assert (
        ProspectSearchCreate(trades=["paysagiste"], validation_mode="automatic").validation_mode
        == ProspectSearchValidationMode.AUTOMATIC
    )


@pytest.mark.parametrize(
    ("status", "prospect_id", "is_pending"),
    [
        (CandidateStatus.KEPT, None, True),
        (CandidateStatus.SET_ASIDE, None, True),
        (CandidateStatus.TO_CONFIRM, None, True),
        (CandidateStatus.KEPT, 12, False),
        (CandidateStatus.SET_ASIDE, 12, False),
        (CandidateStatus.NEEDS_BROWSER, None, False),
        (CandidateStatus.DISCOVERED, None, False),
        (CandidateStatus.REJECTED, None, False),
    ],
)
def test_a_candidate_is_pending_when_it_is_placed_and_not_a_prospect_yet(
    status: CandidateStatus, prospect_id: int | None, is_pending: bool
) -> None:
    candidate = ProspectSearchCandidate(status=status.value, prospect_id=prospect_id)

    assert candidate.is_pending is is_pending


def test_a_request_decides_a_hundred_candidates_at_most() -> None:
    assert len(CandidateDecisions(accept=list(range(60)), reject=list(range(60, 100))).accept) == 60
    with pytest.raises(ValidationError):
        CandidateDecisions(accept=list(range(60)), reject=list(range(60, 101)))


def test_a_candidate_cannot_be_accepted_and_refused_in_the_same_request() -> None:
    with pytest.raises(ValidationError):
        CandidateDecisions(accept=[4, 5], reject=[5])


@pytest.mark.parametrize(
    ("listing_name", "business_name"),
    [
        (
            "A.G Rénovation Couvreur - Réparation de toiture, Démoussage de toiture, Couverture Velux",
            "A.G Rénovation Couvreur",
        ),
        ("SB Rénovation | Couvreur Dijon", "SB Rénovation"),
        ("Cadiou Couverture (couvreur Dijon 21)", "Cadiou Couverture"),
        ("ES Rénovation🏠 Couvreur - Zingueur -", "ES Rénovation Couvreur"),
        ("Weiss-Couvreur zingueur", "Weiss-Couvreur zingueur"),
        ("Garage - Carrosserie Dupont", "Garage - Carrosserie Dupont"),
        ("L'Atelier d'Émile & Fils", "L'Atelier d'Émile & Fils"),
        ('"🌿" Jardins du Chablais', "Jardins du Chablais"),
        ("🏠", "🏠"),
    ],
)
def test_a_listing_title_is_reduced_to_the_business_name(listing_name: str, business_name: str) -> None:
    assert BusinessName.clean(listing_name) == business_name
