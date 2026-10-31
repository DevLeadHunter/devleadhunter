"""Two listings of one search sharing an email, a phone or a registry number are one business: one stays proposed."""

from sqlalchemy.orm import Session

from enums.prospect_search import CandidateOrigin, CandidateRejectReason, CandidateStatus
from models.prospect_search_candidate import ProspectSearchCandidate
from services.prospect_search.candidate_duplicates import CandidateDuplicates

_SEARCH_ID = 17
_USER_ID = 7


def _listing(
    db: Session,
    name: str,
    status: CandidateStatus,
    *,
    keys: list[str],
    reviews: int = 0,
    email_proof_level: str | None = "b",
    reject_reason: CandidateRejectReason | None = None,
    reject_detail: str | None = None,
    prospect_id: int | None = None,
    search_id: int = _SEARCH_ID,
) -> ProspectSearchCandidate:
    """A garage listing of the search, as the search left it."""
    listing = ProspectSearchCandidate(
        search_id=search_id,
        user_id=_USER_ID,
        trade="garage",
        origin=CandidateOrigin.GOOGLE_LOCAL.value,
        name=name,
        country="FR",
        city="Châtellerault",
        status=status.value,
        reject_reason=reject_reason.value if reject_reason else None,
        reject_detail=reject_detail,
        email_proof_level=email_proof_level,
        phone_is_mobile=False,
        google_reviews_count=reviews,
        prospect_id=prospect_id,
        identity_keys=[*keys, f"name:{name.lower()}|chatellerault"],
        evidence=[],
    )
    db.add(listing)
    db.commit()
    return listing


def test_the_better_informed_of_two_listings_sharing_an_email_stays_proposed(db: Session) -> None:
    garage = _listing(
        db,
        "GARAGE CS AUTO",
        CandidateStatus.SET_ASIDE,
        keys=["tel:+33500000051", "mail:garagecsauto@gmail.com"],
        reviews=152,
    )
    body_shop = _listing(
        db,
        "Carrosserie CS Auto",
        CandidateStatus.SET_ASIDE,
        keys=["tel:+33500000052", "fb:100000000000001", "mail:garagecsauto@gmail.com"],
        reviews=26,
        email_proof_level="a",
    )

    moved = CandidateDuplicates.settle(db, body_shop)

    assert moved == [(body_shop, CandidateStatus.SET_ASIDE.value)]
    assert garage.status == CandidateStatus.SET_ASIDE.value
    assert (body_shop.status, body_shop.reject_reason) == (
        CandidateStatus.REJECTED.value,
        CandidateRejectReason.AWAITING_DECISION.value,
    )
    assert (
        body_shop.reject_detail
        == "Même entreprise que « GARAGE CS AUTO », une fiche mieux renseignée de cette recherche."
    )


def test_a_better_informed_listing_found_later_takes_the_place_of_the_first(db: Session) -> None:
    first = _listing(
        db, "Carrosserie CS Auto", CandidateStatus.SET_ASIDE, keys=["mail:garagecsauto@gmail.com"], reviews=26
    )
    later = _listing(db, "GARAGE CS AUTO", CandidateStatus.KEPT, keys=["mail:garagecsauto@gmail.com"], reviews=152)

    CandidateDuplicates.settle(db, later)

    assert later.status == CandidateStatus.KEPT.value
    assert (first.status, first.reject_reason) == (
        CandidateStatus.REJECTED.value,
        CandidateRejectReason.AWAITING_DECISION.value,
    )


def test_two_listings_of_the_same_company_number_are_one_business(db: Session) -> None:
    _listing(db, "Garage Exemple", CandidateStatus.SET_ASIDE, keys=["tel:+33500000053", "reg:123456789"], reviews=40)
    second = _listing(
        db, "Exemple Pneus", CandidateStatus.SET_ASIDE, keys=["tel:+33500000054", "reg:123456789"], reviews=12
    )

    CandidateDuplicates.settle(db, second)

    assert second.reject_reason == CandidateRejectReason.AWAITING_DECISION.value


def test_a_listing_discarded_for_its_website_discards_the_waiting_listings_of_its_business(db: Session) -> None:
    waiting = _listing(db, "Exemple et Fils", CandidateStatus.SET_ASIDE, keys=["mail:garage.exemple@wanadoo.fr"])
    with_website = _listing(
        db,
        "Garage Exemple",
        CandidateStatus.REJECTED,
        keys=["mail:garage.exemple@wanadoo.fr"],
        reject_reason=CandidateRejectReason.HAS_WEBSITE,
        reject_detail="A déjà un site : http://garage-exemple.com/",
    )

    moved = CandidateDuplicates.settle(db, with_website)

    assert moved == [(waiting, CandidateStatus.SET_ASIDE.value)]
    assert (waiting.status, waiting.reject_reason) == (
        CandidateStatus.REJECTED.value,
        CandidateRejectReason.HAS_WEBSITE.value,
    )
    assert (
        waiting.reject_detail == "Même entreprise que « Garage Exemple » : A déjà un site : http://garage-exemple.com/"
    )


def test_a_listing_of_a_business_already_made_a_prospect_is_a_known_business(db: Session) -> None:
    _listing(db, "GARAGE CS AUTO", CandidateStatus.SET_ASIDE, keys=["mail:garagecsauto@gmail.com"], prospect_id=377)
    later = _listing(db, "Carrosserie CS Auto", CandidateStatus.SET_ASIDE, keys=["mail:garagecsauto@gmail.com"])

    CandidateDuplicates.settle(db, later)

    assert (later.reject_reason, later.prospect_id) == (CandidateRejectReason.ALREADY_KNOWN.value, 377)


def test_a_shared_name_another_search_or_a_listing_not_placed_yet_changes_nothing(db: Session) -> None:
    _listing(db, "Garage Exemple", CandidateStatus.SET_ASIDE, keys=["tel:+33500000055"])
    _listing(db, "Garage Exemple Bis", CandidateStatus.SET_ASIDE, keys=["mail:exemple@gmail.com"], search_id=18)
    _listing(db, "Garage Exemple Ter", CandidateStatus.DISCOVERED, keys=["mail:exemple@gmail.com"])
    listing = _listing(db, "Garage Exemple", CandidateStatus.SET_ASIDE, keys=["mail:exemple@gmail.com"])

    assert CandidateDuplicates.settle(db, listing) == []
    assert listing.status == CandidateStatus.SET_ASIDE.value
