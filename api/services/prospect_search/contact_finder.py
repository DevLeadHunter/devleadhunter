"""
Contact finder — the searches that follow a verification when no email came out of it.

In order: look for the business's Facebook page (its « À propos » block is where
tradespeople publish their email), then one wider search whose emails are only kept
with the result that gives them to this business. An email whose domain receives no
mail is dropped before it can bounce.
"""

from __future__ import annotations

import asyncio
import logging

import dns.exception
import dns.resolver

from enums.prospect_search import EmailProofLevel
from scrappers.brightdata_client import BrightDataClient
from scrappers.email_candidate_scoring import GENERIC_EMAIL_PROVIDERS, email_candidate_scorer
from scrappers.facebook_page_urls import FacebookPageUrl
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.search_judge import SearchJudge
from services.prospect_search.trade_catalog import TradeProfile
from services.validation_service import validation_service

logger = logging.getLogger(__name__)

_MAIL_LOOKUP_TIMEOUT_SECONDS: float = 4.0


class EmailDomainCheck:
    """Tells whether the domain of an email receives mail, from its DNS records."""

    def __init__(self) -> None:
        self._verdict_by_domain: dict[str, bool] = {}

    async def receives_mail(self, email: str) -> bool:
        """
        Whether the email's domain has a mail server.

        A lookup that times out is not a proof: only a domain that does not exist, or
        answers with no mail record, makes the email unusable.

        Args:
            email: The address to check.

        Returns:
            False only when the domain provably receives no mail.
        """
        domain = email.rsplit("@", 1)[-1].strip().lower()
        if domain in GENERIC_EMAIL_PROVIDERS:
            return True
        if domain not in self._verdict_by_domain:
            self._verdict_by_domain[domain] = await asyncio.to_thread(self._has_mail_record, domain)
        return self._verdict_by_domain[domain]

    async def drop_dead_email(self, facts: CandidateFacts) -> None:
        """Forget the candidate's email when its domain receives no mail."""
        if facts.email is None or await self.receives_mail(facts.email):
            return
        facts.add_evidence("email_dropped", facts.email, source="Le domaine de cette adresse ne reçoit pas de courrier")
        facts.email = None
        facts.email_proof_level = None

    @staticmethod
    def _has_mail_record(domain: str) -> bool:
        """Blocking DNS lookup of the domain's MX records (an A record is the accepted fallback)."""
        resolver = dns.resolver.Resolver()
        resolver.lifetime = _MAIL_LOOKUP_TIMEOUT_SECONDS
        try:
            resolver.resolve(domain, "MX")
            return True
        except dns.resolver.NXDOMAIN:
            return False
        except dns.resolver.NoAnswer:
            try:
                resolver.resolve(domain, "A")
                return True
            except dns.exception.DNSException:
                return False
        except dns.exception.DNSException:
            return True


class ContactFinder:
    """Looks for the Facebook page and the email of a verified candidate."""

    def __init__(self, client: BrightDataClient, judge: SearchJudge) -> None:
        self._client = client
        self._judge = judge
        self._domain_check = EmailDomainCheck()
        self.judge_call_count: int = 0

    async def find(self, facts: CandidateFacts, trade: TradeProfile) -> None:
        """
        Complete the contact of a candidate that still has no email.

        Args:
            facts: The candidate, completed in place.
            trade: Profile of the searched trade.
        """
        if facts.email is None and facts.facebook_url is None:
            await self._find_facebook_page(facts, trade)
        if facts.email is None and facts.facebook_url is None:
            await self._search_email(facts, trade)
        await self.drop_dead_email(facts)
        await CandidateVerifier.consider_email_domain(facts, trade)

    async def drop_dead_email(self, facts: CandidateFacts) -> None:
        """Forget the candidate's email when its domain receives no mail."""
        await self._domain_check.drop_dead_email(facts)

    async def _find_facebook_page(self, facts: CandidateFacts, trade: TradeProfile) -> None:
        """Search the business on Facebook; an email in its own page's snippet is kept."""
        # The name is not quoted: a page rarely repeats the listing's full name (« … jardinier paysagiste »).
        page = await self._client.google_parsed(
            f"site:facebook.com {facts.name} {facts.town}".strip(), country=facts.country
        )
        if page is None:
            return
        for line in CandidateVerifier.result_lines(page):
            facebook_page = FacebookPageUrl.canonical(line.link)
            if not facebook_page or not CandidateVerifier.is_facebook_page_of(line, facts, trade):
                continue
            if facts.facebook_url is None:
                facts.facebook_url = facebook_page
                facts.add_evidence("facebook", facebook_page, source="Recherche Facebook", url=line.link)
            if facebook_page != facts.facebook_url:
                continue
            for email in self._usable_emails(line.text, facts):
                facts.offer_email(
                    email, EmailProofLevel.DIRECTORY, source="Page Facebook", url=line.link, snippet=line.text
                )

    async def _search_email(self, facts: CandidateFacts, trade: TradeProfile) -> None:
        """One wider search for a business with no Facebook page; the judge says whose each email is."""
        page = await self._client.google_parsed(
            f'"{facts.name}" {facts.town} email OR courriel OR "@"'.strip(), country=facts.country
        )
        if page is None:
            return
        results = CandidateVerifier.result_lines(page)
        candidates = [
            (email, index) for index, line in enumerate(results) for email in self._usable_emails(line.text, facts)
        ]
        if not candidates:
            return
        self.judge_call_count += 1
        verdict = await self._judge.judge(
            name=facts.name,
            city=facts.town,
            trade_label=trade.label,
            google_category=facts.google_category,
            results=results,
        )
        judged = {
            (entry.email, entry.result_index): entry.belongs_to_business
            for entry in (verdict.emails if verdict else [])
        }
        for email, index in candidates:
            line = results[index]
            is_about_business = CandidateVerifier.names_business(line.title, facts, trade)
            if judged.get((email, index)) is False or (judged.get((email, index)) is None and not is_about_business):
                continue
            is_directory_entry = CandidateVerifier.is_known_third_party(line.link, line.host) and is_about_business
            proof = EmailProofLevel.DIRECTORY if is_directory_entry else EmailProofLevel.GUESSED
            facts.offer_email(email, proof, source=line.host, url=line.link, snippet=line.text)

    @staticmethod
    def _usable_emails(text: str, facts: CandidateFacts) -> list[str]:
        """Emails of a text that are well-formed and do not belong to a town hall, a directory or a platform."""
        ranked = email_candidate_scorer.rank_candidates(text, name=facts.name, city=facts.town)
        return [email for email, _ in ranked if validation_service.is_valid_email(email)]
