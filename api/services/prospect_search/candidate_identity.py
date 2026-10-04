"""
Candidate identity — recognising the same business across sources, searches and prospects.

A business is known by several keys at once: its phone number, Google's identifier of
its listing, its Facebook page, its email, and its name in its town. Two records
sharing any key are the same business. The index built here answers, before a single
paid request is spent on a candidate: is it already a prospect, is it flagged « do not
contact », was it discarded by an earlier search?
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from enums.prospect_search import CandidateRejectReason, CandidateStatus
from models.email_log import EmailLog
from models.facebook_exclusion import FacebookPageExclusion
from models.prospect_db import ProspectDB
from models.prospect_search_candidate import ProspectSearchCandidate
from scrappers.facebook_page_urls import FacebookPageUrl
from services.decision_maker.normalize import company_tokens, fold
from services.sms.phone_normalizer import to_e164

_FEATURE_ID_RE: re.Pattern[str] = re.compile(r"0x[0-9a-f]+:0x([0-9a-f]+)", re.IGNORECASE)
_REJECTION_MEMORY: timedelta = timedelta(days=120)
# A rejection worth remembering says something lasting about the business, not about one search's settings.
_LASTING_REJECT_REASONS: tuple[str, ...] = (
    CandidateRejectReason.HAS_WEBSITE.value,
    CandidateRejectReason.CLOSED.value,
    CandidateRejectReason.CHAIN.value,
    CandidateRejectReason.HOMONYM.value,
    CandidateRejectReason.MANUAL.value,
)


class CandidateIdentity:
    """Builds the keys a business is recognised by."""

    @classmethod
    def keys(
        cls,
        *,
        name: str,
        city: str | None,
        country: str,
        phone: str | None = None,
        google_cid: str | None = None,
        facebook_url: str | None = None,
        email: str | None = None,
    ) -> list[str]:
        """
        Every key of a business, strongest first.

        Args:
            name: Business name.
            city: Town of the business.
            country: ISO code, deciding how the phone number is read.
            phone: Phone number in any form.
            google_cid: Google's identifier of the listing.
            facebook_url: Facebook page URL.
            email: Email address.

        Returns:
            The keys that could be built (a business always has at least its name key).
        """
        keys: list[str] = []
        phone_key = cls.phone_key(phone, country)
        if phone_key:
            keys.append(phone_key)
        if google_cid:
            keys.append(f"cid:{google_cid}")
        facebook_key = cls.facebook_key(facebook_url)
        if facebook_key:
            keys.append(facebook_key)
        if email and "@" in email:
            keys.append(f"mail:{email.strip().lower()}")
        keys.append(cls.name_key(name, city))
        return keys

    @staticmethod
    def phone_key(phone: str | None, country: str) -> str | None:
        """Key of a phone number, in international form."""
        e164 = to_e164(phone, country=country) if phone else None
        return f"tel:{e164}" if e164 else None

    @staticmethod
    def facebook_key(facebook_url: str | None) -> str | None:
        """Key of a Facebook page, whatever sub-page or tracking the URL carries."""
        if not facebook_url:
            return None
        canonical = FacebookPageUrl.canonical(facebook_url)
        if not canonical:
            return None
        parsed = urlparse(canonical)
        page_id = parse_qs(parsed.query).get("id", [""])[0]
        return f"fb:{(page_id or parsed.path.strip('/')).lower()}"

    @staticmethod
    def name_key(name: str, city: str | None) -> str:
        """Key of a name in a town: word order, accents, legal forms and punctuation do not count."""
        tokens = sorted(company_tokens(name)) or [fold(name)]
        return f"name:{' '.join(tokens)}|{fold(city or '')}"

    @staticmethod
    def cid_of_maps_url(google_maps_url: str | None) -> str | None:
        """Google's identifier read from a Maps URL (``?cid=`` form or ``0x…:0x…`` feature id)."""
        if not google_maps_url:
            return None
        cid = parse_qs(urlparse(google_maps_url).query).get("cid", [""])[0]
        if cid.isdigit():
            return cid
        feature_id = _FEATURE_ID_RE.search(google_maps_url)
        return str(int(feature_id.group(1), 16)) if feature_id else None


@dataclass(frozen=True)
class KnownBusiness:
    """Why a candidate is not a new business for the user."""

    reason: CandidateRejectReason
    detail: str
    prospect_id: int | None


class KnownBusinessIndex:
    """Keys of the businesses a search must not process again."""

    def __init__(self) -> None:
        self._prospect_id_by_key: dict[str, int] = {}
        self._do_not_contact_keys: set[str] = set()
        self._contacted_keys: set[str] = set()
        self._rejected_keys: set[str] = set()
        self._awaiting_decision_keys: set[str] = set()

    @classmethod
    def load(cls, db: Session, *, user_id: int, organization_id: int | None, search_id: int) -> KnownBusinessIndex:
        """
        Read the user's prospects and the candidates earlier searches discarded.

        Args:
            db: Active database session.
            user_id: Owner of the search.
            organization_id: The user's organization, whose shared prospects count as known.
            search_id: The running search, whose own candidates are not « earlier » rejections.

        Returns:
            The index, ready to answer :meth:`match`.
        """
        index = cls()
        scope = ProspectDB.user_id == user_id
        if organization_id is not None:
            scope = or_(scope, ProspectDB.organization_id == organization_id)
        for prospect in db.execute(select(ProspectDB).where(scope)).scalars():
            phones = [prospect.phone, *(prospect.phones or [])]
            emails = [prospect.email, *(prospect.emails or [])]
            keys = CandidateIdentity.keys(
                name=prospect.name,
                city=prospect.city,
                country=prospect.country or "FR",
                google_cid=CandidateIdentity.cid_of_maps_url(prospect.google_maps_url),
                facebook_url=prospect.facebook_url,
            )
            phone_keys = (CandidateIdentity.phone_key(phone, prospect.country or "FR") for phone in phones)
            keys += [key for key in phone_keys if key]
            keys += [f"mail:{email.strip().lower()}" for email in emails if email]
            for key in keys:
                index._prospect_id_by_key.setdefault(key, prospect.id)
                if prospect.do_not_contact:
                    index._do_not_contact_keys.add(key)

        since = naive_utc_now() - _REJECTION_MEMORY
        rejected = db.execute(
            select(ProspectSearchCandidate.identity_keys).where(
                ProspectSearchCandidate.user_id == user_id,
                ProspectSearchCandidate.search_id != search_id,
                ProspectSearchCandidate.status == CandidateStatus.REJECTED.value,
                ProspectSearchCandidate.reject_reason.in_(_LASTING_REJECT_REASONS),
                ProspectSearchCandidate.created_at >= since,
            )
        ).scalars()
        for keys in rejected:
            index._rejected_keys.update(key for key in (keys or []) if not key.startswith("name:"))

        awaiting = db.execute(
            select(ProspectSearchCandidate.identity_keys).where(
                ProspectSearchCandidate.user_id == user_id,
                ProspectSearchCandidate.search_id != search_id,
                ProspectSearchCandidate.is_pending,
            )
        ).scalars()
        for keys in awaiting:
            index._awaiting_decision_keys.update(key for key in (keys or []) if not key.startswith("name:"))

        # An address already written to stays known even when its prospect was deleted since.
        contacted = db.execute(select(EmailLog.recipient_email).where(EmailLog.user_id == user_id).distinct()).scalars()
        index._contacted_keys.update(f"mail:{email.strip().lower()}" for email in contacted if email)

        # Pages the former Facebook search discarded for owning a website.
        discarded_pages = db.execute(
            select(FacebookPageExclusion.page_url).where(
                FacebookPageExclusion.user_id == user_id, FacebookPageExclusion.reason == "has_website"
            )
        ).scalars()
        index._rejected_keys.update(
            key for key in (CandidateIdentity.facebook_key(page_url) for page_url in discarded_pages) if key
        )
        return index

    def match(self, keys: list[str]) -> KnownBusiness | None:
        """
        Tell why a business must be skipped, if it must.

        Args:
            keys: Identity keys of the candidate.

        Returns:
            Why it is already known, or ``None`` for a new business.
        """
        for key in keys:
            if key in self._do_not_contact_keys:
                return KnownBusiness(
                    CandidateRejectReason.DO_NOT_CONTACT,
                    "Marqué « ne plus contacter » dans vos prospects.",
                    self._prospect_id_by_key.get(key),
                )
        for key in keys:
            if key in self._prospect_id_by_key:
                return KnownBusiness(
                    CandidateRejectReason.ALREADY_KNOWN, "Déjà dans vos prospects.", self._prospect_id_by_key[key]
                )
        if any(key in self._contacted_keys for key in keys):
            return KnownBusiness(CandidateRejectReason.ALREADY_KNOWN, "Son adresse a déjà reçu un de vos emails.", None)
        if any(key in self._awaiting_decision_keys for key in keys):
            return KnownBusiness(
                CandidateRejectReason.AWAITING_DECISION,
                "Déjà proposé par une recherche précédente : il attend votre validation.",
                None,
            )
        if any(key in self._rejected_keys for key in keys):
            return KnownBusiness(
                CandidateRejectReason.PREVIOUSLY_REJECTED, "Déjà écarté par une recherche précédente.", None
            )
        return None

    def remember_prospect(self, keys: list[str], prospect_id: int) -> None:
        """Record a prospect created during the run, so the same run never creates it twice."""
        for key in keys:
            self._prospect_id_by_key.setdefault(key, prospect_id)
