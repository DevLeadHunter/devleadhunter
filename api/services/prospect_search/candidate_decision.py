"""
Candidate decision — from the facts of a candidate to its place in the search.

One rule set, applied the same way to every candidate: discard what the objective
excludes (website, closed, chain, wrong trade, low rating), keep what the chosen
channel can reach, set aside what another channel could, and leave to the user what
the search could not prove.
"""

from __future__ import annotations

from dataclasses import dataclass

from enums.prospect_search import (
    CandidateOrigin,
    CandidateRejectReason,
    CandidateStatus,
    EmailProofLevel,
    ProspectSearchChannel,
)
from enums.website_status import WebsiteStatus
from models.prospect_search import ProspectSearch
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.name_in_address import NameInAddress
from services.prospect_search.network_outlets import NetworkOutlets
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
        if facts.is_swiss_directory_unanswered:
            return CandidateVerdict(
                CandidateStatus.TO_CONFIRM,
                detail="L'annuaire suisse n'a pas répondu : l'astérisque « pas de publicité » n'a pas été lu.",
            )
        register_successor = facts.register_successor
        if register_successor is not None:
            return CandidateVerdict(
                CandidateStatus.TO_CONFIRM,
                detail=(
                    f"Le registre du commerce donne « {register_successor.get('snippet')} », et "
                    f"« {register_successor['value']} » est inscrite à {facts.town} : à vérifier, "
                    "l'atelier continue peut-être sous ce nom."
                ),
            )
        if facts.has_email_on_another_site and facts.email is not None:
            return CandidateVerdict(
                CandidateStatus.TO_CONFIRM,
                detail=(
                    f"Son email est sur {facts.email.rsplit('@', 1)[-1]}, un site en ligne qui ne le nomme pas : "
                    "à vérifier."
                ),
            )
        has_untraced_website = (
            facts.has_website_button is True
            and (facts.website is None or facts.is_website_guessed_from_email_domain)
            and not facts.is_facebook_page_the_listed_website
        )
        if criteria.only_without_website and has_untraced_website:
            return CandidateVerdict(
                CandidateStatus.TO_CONFIRM,
                detail="Un site est déclaré sur sa fiche Google, mais il n'a pas été retrouvé : à vérifier.",
            )
        technical_address = facts.website_technical_address
        is_reachable = has_proven_email or has_guessed_email or has_mobile
        if criteria.only_without_website and technical_address is not None and facts.website is None and is_reachable:
            return CandidateVerdict(
                CandidateStatus.TO_CONFIRM,
                detail=(
                    f"{technical_address['source']} lui donne {technical_address['value']}, l'adresse technique d'un "
                    "site : il a sans doute un site, qui n'a pas été retrouvé : à vérifier."
                ),
            )
        place_elsewhere = facts.contact_elsewhere
        if place_elsewhere is not None and facts.email is not None:
            return CandidateVerdict(
                CandidateStatus.TO_CONFIRM,
                detail=(
                    f"{place_elsewhere['source']} ({place_elsewhere.get('url') or facts.email}) désigne un autre "
                    f"endroit ({place_elsewhere['value']}) que {facts.town} : à vérifier, ce peut être un homonyme."
                ),
            )
        email_person_mismatch = NameInAddress.email_person_mismatch(facts.email, facts) if facts.email else None
        if email_person_mismatch is not None:
            return CandidateVerdict(
                CandidateStatus.TO_CONFIRM,
                detail=(
                    f"Son email ({facts.email}) porte le nom de {email_person_mismatch.email_person}, mais "
                    f"{email_person_mismatch.named_by} nomme {email_person_mismatch.named_person} : à vérifier, ce "
                    "n'est peut-être pas son adresse."
                ),
            )
        is_page_without_phone = (
            facts.origin == CandidateOrigin.FACEBOOK_SEARCH.value and facts.is_facebook_page_read and not facts.phone
        )
        if is_page_without_phone and (has_proven_email or has_guessed_email):
            return CandidateVerdict(
                CandidateStatus.TO_CONFIRM,
                detail="Page Facebook sans téléphone : rien ne montre que c'est un artisan du coin, à vérifier.",
            )
        is_page_without_trade_name = facts.origin == CandidateOrigin.FACEBOOK_SEARCH.value and not trade.names_trade(
            facts.name
        )
        if is_page_without_trade_name and (has_proven_email or has_guessed_email):
            return CandidateVerdict(
                CandidateStatus.TO_CONFIRM,
                detail="Page Facebook dont le nom ne dit pas le métier : à vérifier (association, groupe, agence…).",
            )
        if facts.is_placed_by_the_search_only and (has_proven_email or has_mobile):
            return CandidateVerdict(
                CandidateStatus.TO_CONFIRM,
                detail=f"Sa fiche Google ne donne pas d'adresse : rien ne montre qu'il est à {facts.town}, à vérifier.",
            )
        if facts.is_addressed_at_town_hall and (has_proven_email or has_guessed_email or has_mobile):
            return CandidateVerdict(
                CandidateStatus.TO_CONFIRM,
                detail=(
                    "Sa fiche Google donne l'adresse de la mairie et aucune entreprise de son nom n'est inscrite dans "
                    "le département : une commune de rattachement, pas un atelier ? À vérifier."
                ),
            )
        registered_activity = facts.activity_of_another_trade
        if registered_activity is not None and (has_proven_email or has_guessed_email or has_mobile):
            return CandidateVerdict(
                CandidateStatus.TO_CONFIRM,
                detail=(
                    f"Le registre inscrit « {registered_activity.get('snippet') or facts.name} » sous une autre "
                    f"activité ({registered_activity['value']}) : à vérifier, ce n'est peut-être pas un "
                    f"{trade.label.lower()}."
                ),
            )
        if cls._meets_channel(criteria.channel, has_email=has_proven_email, has_mobile=has_mobile):
            return CandidateVerdict(CandidateStatus.KEPT)
        if not has_proven_email and can_read_facebook_page and criteria.channel != ProspectSearchChannel.SMS:
            return CandidateVerdict(
                CandidateStatus.NEEDS_BROWSER, detail="Sa page Facebook reste à lire pour y chercher son email."
            )
        if has_guessed_email:
            return CandidateVerdict(CandidateStatus.TO_CONFIRM, detail=cls._guessed_email_detail(facts))
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
    def _guessed_email_detail(facts: CandidateFacts) -> str:
        """Why an email without a frank proof is left to the user: it may even name another business."""
        if facts.email is not None and NameInAddress.email_names_another_business(facts.email, facts):
            return f"Son email ({facts.email}) porte le nom d'une autre affaire : à vérifier."
        if facts.is_email_beside_another_phone:
            return (
                f"Son email ({facts.email}) est écrit à côté d'un autre numéro que le sien : à vérifier, ce peut être "
                "un homonyme."
            )
        if facts.is_email_unplaced:
            return f"La page qui donne son email ({facts.email}) ne dit pas où il est : à vérifier, ce peut être un homonyme."
        return "Un email a été trouvé sans preuve franche qu'il lui appartient : à vous de voir."

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
            return cls._rejected(CandidateRejectReason.CLOSED, cls._closed_detail(facts))
        if facts.is_abroad:
            return cls._rejected(
                CandidateRejectReason.OUT_OF_COUNTRY,
                f"Adresse dans un autre pays que la recherche : {facts.address}"
                if facts.address
                else f"Numéro d'un autre pays que la recherche : {facts.phone}",
            )
        searched_department = facts.searched_department
        if searched_department is not None and facts.is_outside_region:
            return cls._rejected(
                CandidateRejectReason.OUT_OF_COUNTRY,
                f"Hors de la zone de la recherche ({searched_department.label}) : {facts.address or facts.phone}",
            )
        if facts.refuses_advertising:
            return cls._rejected(
                CandidateRejectReason.NO_ADVERTISING,
                "Refuse la publicité dans l'annuaire suisse (astérisque) : la loi interdit de le démarcher.",
            )
        if facts.is_other_business:
            return cls._rejected(
                CandidateRejectReason.HOMONYM, "Google montre une autre entreprise du même nom, dans une autre ville."
            )
        if facts.is_chain or NetworkOutlets.facebook_page_names_network(facts.facebook_url):
            return cls._rejected(CandidateRejectReason.CHAIN, cls._chain_detail(facts))
        if facts.registered_association is not None:
            return cls._rejected(
                CandidateRejectReason.WRONG_TRADE,
                f"Inscrit au registre comme association ({facts.registered_association}) : pas une entreprise.",
            )
        if trade.names_another_trade(facts.name):
            return cls._rejected(
                CandidateRejectReason.WRONG_TRADE, f"Son nom dit un autre métier que celui cherché : « {facts.name} »."
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
    def _chain_detail(facts: CandidateFacts) -> str:
        """The network a discarded outlet belongs to: a brand it is the agent or dealer of, its Facebook page's, a chain."""
        if facts.outlet_brand is not None:
            return f"Agent ou concessionnaire {facts.outlet_brand} : le patron ne décide pas seul."
        if not facts.is_chain:
            return "Sa page Facebook porte le nom d'un réseau : le patron ne décide pas seul."
        return "Enseigne de réseau ou franchise : le patron ne décide pas seul."

    @staticmethod
    def _closed_detail(facts: CandidateFacts) -> str:
        """Where the closing was read: the Google listing, or a register writing the company in liquidation."""
        closing = next((line for line in facts.evidence if line.get("fact") == "closed"), None)
        if closing is None or closing.get("source") == "Fiche Google":
            return "Fiche Google marquée fermée."
        return f"Société {closing['value']} selon {closing['source']}."

    @staticmethod
    def _rejected(reason: CandidateRejectReason, detail: str) -> CandidateVerdict:
        """A discarded verdict."""
        return CandidateVerdict(CandidateStatus.REJECTED, reason, detail)
