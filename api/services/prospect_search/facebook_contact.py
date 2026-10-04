"""
Facebook contact — what a browser read on a candidate's Facebook page, and what it changes.

The search runs on the server, which cannot open Facebook. A browser on the user's
machine (the desktop app, or the API itself when it runs on a workstation) reads the
page's contact block and hands it over here: the email becomes the best-proven one
(the business published it itself), a website shown on the page is checked, and the
candidate gets its final place.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.database import SessionLocal
from enums.prospect_search import CandidateStatus, EmailProofLevel, ProspectSearchValidationMode
from models.prospect_search import ProspectSearch
from models.prospect_search_candidate import ProspectSearchCandidate
from scrappers.email_candidate_scoring import email_candidate_scorer
from services.organization_service import organization_service
from services.prospect_search.candidate_decision import CandidateDecision, CandidateVerdict, SearchCriteria
from services.prospect_search.candidate_identity import KnownBusinessIndex
from services.prospect_search.candidate_store import CandidateStore
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.contact_finder import EmailDomainCheck
from services.prospect_search.trade_catalog import TradeCatalog
from services.validation_service import validation_service
from services.website_liveness_service import website_liveness_service


@dataclass(frozen=True)
class FacebookContactRead:
    """Contact block of a Facebook page, as a browser read it."""

    is_readable: bool
    emails: list[str] = field(default_factory=list)
    phone: str | None = None
    website: str | None = None


class FacebookContactRecorder:
    """Applies a Facebook page read to the candidate it was asked for."""

    def __init__(self) -> None:
        self._domain_check = EmailDomainCheck()

    async def record(self, candidate_id: int, read: FacebookContactRead) -> CandidateVerdict | None:
        """
        Complete a waiting candidate with what its Facebook page says, and place it.

        Its prospect is created here only in an automatic search; in a manual one the
        placed candidate waits for the user's decision.

        Args:
            candidate_id: The candidate whose page was read.
            read: What the browser found.

        Returns:
            The candidate's new verdict, or ``None`` when it was not waiting for a read
            (another read of the same page may have settled it meanwhile).
        """
        with SessionLocal() as db:
            row = db.get(ProspectSearchCandidate, candidate_id)
            if row is None or row.status != CandidateStatus.NEEDS_BROWSER.value:
                return None
            search = db.get(ProspectSearch, row.search_id)
            if search is None:
                return None
            facts = CandidateStore.facts_of(row)
            trade = TradeCatalog.resolve(row.trade)
            criteria = SearchCriteria.of_search(search)
            organization_id = organization_service.user_org_id(db, row.user_id)
            creates_prospect = search.validation_mode == ProspectSearchValidationMode.AUTOMATIC.value

        facts.is_verified = True
        facts.is_facebook_page_read = True
        page_url = facts.facebook_url or ""
        if not read.is_readable:
            facts.add_evidence("facebook_unread", "page illisible sans connexion", source="Page Facebook", url=page_url)
        else:
            for email in read.emails:
                cleaned = email.strip().lower()
                is_usable = validation_service.is_valid_email(cleaned) and not (
                    email_candidate_scorer.belongs_to_an_institution(cleaned, city=facts.town)
                )
                if is_usable and facts.offer_email(
                    cleaned, EmailProofLevel.PUBLISHED, source="Page Facebook", url=page_url
                ):
                    break
            if read.phone and not facts.phone:
                facts.phone = read.phone
                facts.add_evidence("phone", read.phone, source="Page Facebook", url=page_url)
            if read.website and facts.website is None and validation_service.is_valid_website(read.website):
                facts.website = read.website
                status = await website_liveness_service.check_website_status(read.website)
                facts.website_status = status.value if status is not None else None
                facts.add_evidence("website", read.website, source="Page Facebook", url=page_url)

        await self._domain_check.drop_dead_email(facts)
        await CandidateVerifier.consider_email_domain(facts, trade)

        verdict = CandidateDecision.decide(facts, trade, criteria)
        with SessionLocal() as db:
            row = db.get(ProspectSearchCandidate, candidate_id)
            if row is None or row.status != CandidateStatus.NEEDS_BROWSER.value:
                return None
            # The page may reveal an email the user already wrote to, or one of an existing prospect.
            known = KnownBusinessIndex.load(
                db, user_id=row.user_id, organization_id=organization_id, search_id=row.search_id
            ).match(CandidateStore.identity_keys(facts))
            if known is not None and verdict.status != CandidateStatus.REJECTED:
                verdict = CandidateVerdict(CandidateStatus.REJECTED, known.reason, known.detail)
            CandidateStore.write_back(row, facts, verdict)
            db.commit()
            if creates_prospect:
                await CandidateStore.promote_or_leave_to_confirm(db, row, facts, trade, organization_id=organization_id)
            return CandidateStore.verdict_of(row)


facebook_contact_recorder = FacebookContactRecorder()
