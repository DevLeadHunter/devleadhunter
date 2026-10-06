"""
Candidate decision — from the facts of a candidate to its place in the search.

One rule set, applied the same way to every candidate: discard what the objective
excludes (website, closed, chain, wrong trade, low rating), keep what the chosen
channel can reach, set aside what another channel could, and leave to the user what
the search could not prove.
"""

from __future__ import annotations

from dataclasses import dataclass

from enums.prospect_search import CandidateRejectReason, CandidateStatus, EmailProofLevel, ProspectSearchChannel
from enums.website_status import WebsiteStatus
from models.prospect_search import ProspectSearch
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.trade_catalog import TradeProfile

# A rating read on fewer reviews says too little to discard a business.
_MINIMUM_REVIEWS_FOR_RATING_FLOOR: int = 3


@dataclass(frozen=True)
class SearchCriteria:
    """What the user asked the kept prospects to be."""

    channel: ProspectSearchChannel
    only_without_website: bool
    minimum_rating: float | None

    @classmethod
    def of_search(cls, search: ProspectSearch) -> SearchCriteria:
        """The criteria a stored search asks for."""
        return cls(
            channel=ProspectSearchChannel(search.channel),
            only_without_website=search.only_without_website,
            minimum_rating=search.minimum_rating,
        )


@dataclass(frozen=True)
class CandidateVerdict:
    """Where a candidate goes, and why when it is discarded or set aside."""

    status: CandidateStatus
    reject_reason: CandidateRejectReason | None = None
    detail: str | None = None


class CandidateDecision:
    """Decides the status of a candidate from its facts."""

    @classmethod
    def decide(cls, facts: CandidateFacts, trade: TradeProfile, criteria: SearchCriteria) -> CandidateVerdict:
        """
        Place a candidate.

        Args:
            facts: Everything read about the candidate.
            trade: Profile of the searched trade.
            criteria: The objective's criteria.

        Returns:
            The status, with the reason and a plain-words detail when it is not simply kept.
        """
        rejection = cls._rejection(facts, trade, criteria)
        if rejection is not None:
            return rejection

        has_proven_email = facts.email is not None and facts.email_proof_level != EmailProofLevel.GUESSED.value
        has_guessed_email = facts.email is not None and not has_proven_email
        has_mobile = facts.has_mobile_phone
        can_read_facebook_page = facts.facebook_url is not None and not facts.is_facebook_page_read

        if not facts.is_verified:
            return CandidateVerdict(
                CandidateStatus.TO_CONFIRM, detail="La vérification sur Google n'a pas répondu : fiche non contrôlée."
            )
        has_untraced_website = facts.has_website_button is True and facts.website is None and facts.facebook_url is None
        if criteria.only_without_website and has_untraced_website:
            return CandidateVerdict(
                CandidateStatus.TO_CONFIRM,
                detail="Un site est déclaré sur sa fiche Google, mais il n'a pas été retrouvé : à vérifier.",
            )
        if cls._meets_channel(criteria.channel, has_email=has_proven_email, has_mobile=has_mobile):
            return CandidateVerdict(CandidateStatus.KEPT)
        if not has_proven_email and can_read_facebook_page and criteria.channel != ProspectSearchChannel.SMS:
            return CandidateVerdict(
                CandidateStatus.NEEDS_BROWSER, detail="Sa page Facebook reste à lire pour y chercher son email."
            )
        if has_guessed_email:
            return CandidateVerdict(
                CandidateStatus.TO_CONFIRM,
                detail="Un email a été trouvé sans preuve franche qu'il lui appartient : à vous de voir.",
            )
        if has_proven_email or has_mobile:
            return CandidateVerdict(
                CandidateStatus.SET_ASIDE, detail=cls._set_aside_detail(has_proven_email, has_mobile)
            )
        return CandidateVerdict(
            CandidateStatus.REJECTED, CandidateRejectReason.NO_CONTACT, "Ni email ni numéro de portable trouvés."
        )

    @staticmethod
    def _meets_channel(channel: ProspectSearchChannel, *, has_email: bool, has_mobile: bool) -> bool:
        """Whether the contact found is the one the objective asks for."""
        if channel == ProspectSearchChannel.SMS:
            return has_mobile
        if channel == ProspectSearchChannel.EMAIL_AND_SMS:
            return has_email and has_mobile
        return has_email

    @staticmethod
    def _set_aside_detail(has_email: bool, has_mobile: bool) -> str:
        """Why a reachable candidate does not count toward the objective."""
        if has_mobile and not has_email:
            return "Portable sans email : joignable par SMS."
        if has_email and not has_mobile:
            return "Email sans portable : joignable par email."
        return "Un seul moyen de contact."

    @classmethod
    def _rejection(
        cls, facts: CandidateFacts, trade: TradeProfile, criteria: SearchCriteria
    ) -> CandidateVerdict | None:
        """The reason a candidate is out of the objective, if any."""
        if facts.is_closed:
            return cls._rejected(CandidateRejectReason.CLOSED, "Fiche Google marquée fermée.")
        if facts.refuses_advertising:
            return cls._rejected(
                CandidateRejectReason.NO_ADVERTISING,
                "Refuse la publicité dans l'annuaire suisse (astérisque) : la loi interdit de le démarcher.",
            )
        if facts.is_other_business:
            return cls._rejected(
                CandidateRejectReason.HOMONYM, "Google montre une autre entreprise du même nom, dans une autre ville."
            )
        if facts.is_chain:
            return cls._rejected(
                CandidateRejectReason.CHAIN, "Enseigne de réseau ou franchise : le patron ne décide pas seul."
            )
        if not facts.matches_trade or not trade.accepts_category(facts.google_category):
            category = facts.google_category or "autre activité"
            return cls._rejected(
                CandidateRejectReason.WRONG_TRADE, f"Activité différente du métier cherché ({category})."
            )
        has_live_website = facts.website is not None and facts.website_status == WebsiteStatus.LIVE.value
        has_unread_website = facts.website is None and facts.has_website_button is True and not facts.is_verified
        if criteria.only_without_website and has_live_website:
            return cls._rejected(CandidateRejectReason.HAS_WEBSITE, f"A déjà un site : {facts.website}")
        if criteria.only_without_website and has_unread_website:
            return cls._rejected(CandidateRejectReason.HAS_WEBSITE, "Un site est déclaré sur sa fiche Google.")
        is_rating_meaningful = (facts.google_reviews_count or 0) >= _MINIMUM_REVIEWS_FOR_RATING_FLOOR
        if (
            criteria.minimum_rating is not None
            and facts.google_rating is not None
            and is_rating_meaningful
            and facts.google_rating < criteria.minimum_rating
        ):
            return cls._rejected(
                CandidateRejectReason.LOW_RATING,
                f"Note Google {facts.google_rating:.1f} sur {facts.google_reviews_count} avis, sous le seuil demandé.",
            )
        return None

    @staticmethod
    def _rejected(reason: CandidateRejectReason, detail: str) -> CandidateVerdict:
        """A discarded verdict."""
        return CandidateVerdict(CandidateStatus.REJECTED, reason, detail)
