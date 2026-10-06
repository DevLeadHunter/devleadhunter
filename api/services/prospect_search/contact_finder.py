"""
Contact finder — the searches that follow a verification when no email came out of it.

In order: look for the business's Facebook page (its « À propos » block is where
tradespeople publish their email), then one wider search whose emails are only kept
with the result that gives them to this business, then the phone number itself, which
directories list under names the listing does not use. An email whose domain receives
no mail is dropped before it can bounce.
"""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import urlparse

import dns.exception
import dns.resolver

from enums.prospect_search import EmailProofLevel
from scrappers.brightdata_client import BrightDataClient
from scrappers.email_candidate_scoring import GENERIC_EMAIL_PROVIDERS, email_candidate_scorer
from scrappers.facebook_page_urls import FacebookPageUrl
from services.country_profiles import CountryProfiles
from services.decision_maker.normalize import fold
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.search_judge import SearchJudge, SearchResultLine
from services.prospect_search.trade_catalog import TradeProfile
from services.validation_service import validation_service
from services.website_liveness_service import website_liveness_service

logger = logging.getLogger(__name__)

_MAIL_LOOKUP_TIMEOUT_SECONDS: float = 4.0
_REFERENCE_MAIL_DOMAIN: str = "gmail.com"
_PUBLIC_RESOLVERS: tuple[str, ...] = ("8.8.8.8", "1.1.1.1")
# National numbers are nine digits after the trunk zero in France, Switzerland and Belgium.
_PHONE_MATCH_DIGITS: int = 9
_QUOTED_NAME_MAXIMUM_WORDS: int = 3
_NON_DIGITS_RE: re.Pattern[str] = re.compile(r"\D")
_PHONE_NUMBER_RE: re.Pattern[str] = re.compile(r"(?:\+|\b0)\d{1,3}(?:[\s./-]?\d{2,3}){3,4}\b")
_LEGAL_NOTICE_WORDS: tuple[str, ...] = ("mentions legales", "impressum")
_INTERNATIONAL_COUNTRY_DOMAINS: tuple[str, ...] = (".eu", ".io", ".co", ".me", ".tv", ".ai")


class EmailDomainCheck:
    """Tells whether the domain of an email receives mail, from its DNS records."""

    def __init__(self) -> None:
        self._verdict_by_domain: dict[str, bool] = {}

    async def receives_mail(self, email: str) -> bool:
        """
        Whether the email's domain has a mail server.

        A lookup that times out is not a proof: only a domain that does not exist, answers
        with no mail record, or whose name servers all fail while the resolver works, makes
        the email unusable.

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
            return not EmailDomainCheck._name_servers_fail(domain)

    @staticmethod
    def _name_servers_fail(domain: str) -> bool:
        """
        Whether the domain's own name servers fail, asked again through public resolvers.

        A slow lookup proves nothing; every server answering with a failure does, once the
        same resolvers answer for a domain known to receive mail.
        """
        public_resolver = dns.resolver.Resolver(configure=False)
        public_resolver.nameservers = list(_PUBLIC_RESOLVERS)
        public_resolver.lifetime = _MAIL_LOOKUP_TIMEOUT_SECONDS
        try:
            public_resolver.resolve(domain, "MX")
            return False
        except dns.resolver.NoNameservers:
            return EmailDomainCheck._answers_for_reference_domain(public_resolver)
        except dns.exception.DNSException:
            return False

    @staticmethod
    def _answers_for_reference_domain(resolver: dns.resolver.Resolver) -> bool:
        """Whether the resolver answers for a domain known to receive mail."""
        try:
            resolver.resolve(_REFERENCE_MAIL_DOMAIN, "MX")
            return True
        except dns.exception.DNSException:
            return False


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
        if facts.email is None and facts.phone:
            await self._search_by_phone(facts, trade)
        if facts.website and facts.website_status is None:
            status = await website_liveness_service.check_website_status(facts.website)
            facts.website_status = status.value if status is not None else None
        await self.drop_dead_email(facts)
        await CandidateVerifier.consider_email_domain(facts, trade)
        await CandidateVerifier.consider_email_source_site(facts, trade)

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
            if self._shows_only_other_phones(line.text, facts):
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
            f'{self._name_to_search(facts)} {facts.town} email OR courriel OR "@"'.strip(),
            country=facts.country,
        )
        if page is None:
            return
        results = CandidateVerifier.result_lines(page)
        candidates = [
            (email, index)
            for index, line in enumerate(results)
            if not self._is_unreliable_source(line, facts)
            for email in self._usable_emails(line.text, facts)
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
            is_named_without_another_phone = CandidateVerifier.names_business(
                line.title, facts, trade
            ) and not self._shows_only_other_phones(line.text, facts)
            is_about_business = is_named_without_another_phone or self._shows_phone(line.text, facts)
            if is_about_business:
                CandidateVerifier.read_no_advertising_mark(facts, line)
            if judged.get((email, index)) is False or (judged.get((email, index)) is None and not is_about_business):
                continue
            is_directory_entry = CandidateVerifier.is_known_third_party(line.link, line.host) and is_about_business
            proof = EmailProofLevel.DIRECTORY if is_directory_entry else EmailProofLevel.GUESSED
            facts.offer_email(email, proof, source=line.host, url=line.link, snippet=line.text)

    @staticmethod
    def _name_to_search(facts: CandidateFacts) -> str:
        """
        The name as a search should carry it.

        A short name is quoted. A long listing title (« Architecte paysagiste Déco-Jardin Sàrl »)
        is written nowhere else word for word, so it is searched unquoted.
        """
        is_long_title = len(facts.name.split()) > _QUOTED_NAME_MAXIMUM_WORDS
        return facts.name if is_long_title else f'"{facts.name}"'

    @staticmethod
    def _shows_phone(text: str, facts: CandidateFacts) -> bool:
        """Whether a text shows the candidate's phone number, however it is spaced."""
        phone_digits = _NON_DIGITS_RE.sub("", facts.phone or "")
        if len(phone_digits) < _PHONE_MATCH_DIGITS:
            return False
        return phone_digits[-_PHONE_MATCH_DIGITS:] in _NON_DIGITS_RE.sub("", text)

    @staticmethod
    def _shows_only_other_phones(text: str, facts: CandidateFacts) -> bool:
        """Whether a text shows phone numbers, none of them the candidate's: the page of a namesake."""
        own_digits = _NON_DIGITS_RE.sub("", facts.phone or "")
        if len(own_digits) < _PHONE_MATCH_DIGITS:
            return False
        shown_numbers = [_NON_DIGITS_RE.sub("", number) for number in _PHONE_NUMBER_RE.findall(text)]
        return bool(shown_numbers) and all(
            number[-_PHONE_MATCH_DIGITS:] != own_digits[-_PHONE_MATCH_DIGITS:] for number in shown_numbers
        )

    async def _search_by_phone(self, facts: CandidateFacts, trade: TradeProfile) -> None:
        """
        Search the phone number itself: directories list a business under names the listing does not use.

        A directory result showing the candidate's number is about the candidate, whatever name it
        carries; the one email it shows next to the number is kept as given by a third party. Any
        other site must name the business in its title: a home number is shared with a relative's
        own activity (a gallery, a shop). A result showing several emails is a list of businesses
        and proves nothing.
        """
        phone_digits = _NON_DIGITS_RE.sub("", facts.phone or "")
        if len(phone_digits) < _PHONE_MATCH_DIGITS:
            return
        page = await self._client.google_parsed(
            f'"{(facts.phone or "").strip()}" OR "{phone_digits}"', country=facts.country
        )
        if page is None:
            return
        for line in CandidateVerifier.result_lines(page):
            if not self._shows_phone(line.text, facts) or self._is_foreign_page(line, facts):
                continue
            CandidateVerifier.read_no_advertising_mark(facts, line)
            if self._is_legal_notice_of_a_website(line):
                site = urlparse(line.link)
                CandidateVerifier.consider_website(
                    facts,
                    f"{site.scheme}://{site.netloc}/",
                    source="Ses mentions légales montrent son numéro",
                    proof_url=line.link,
                )
            if self._is_unreliable_source(line, facts):
                continue
            is_directory_page = CandidateVerifier.is_known_third_party(
                line.link, line.host
            ) and not validation_service.is_social_url(line.link)
            if not (is_directory_page or CandidateVerifier.names_business(line.title, facts, trade)):
                continue
            emails = self._usable_emails(line.text, facts)
            if len(emails) == 1:
                facts.offer_email(
                    emails[0], EmailProofLevel.DIRECTORY, source=line.host, url=line.link, snippet=line.text
                )

    @classmethod
    def _is_unreliable_source(cls, line: SearchResultLine, facts: CandidateFacts) -> bool:
        """Whether a result can show the candidate's number beside a stranger's email: a group post, a document, a foreign page."""
        is_shared_page = CandidateVerifier.is_group_discussion(line.link) or cls._is_downloaded_document(line.link)
        return is_shared_page or cls._is_foreign_page(line, facts)

    @staticmethod
    def _is_foreign_page(line: SearchResultLine, facts: CandidateFacts) -> bool:
        """Whether a result sits on another country's domain, where the same digits make another number (« 06 … » in Rome)."""
        country_domain = f".{line.host.rsplit('.', 1)[-1]}"
        is_country_domain = len(country_domain) == 3 and country_domain not in _INTERNATIONAL_COUNTRY_DOMAINS
        return is_country_domain and country_domain not in CountryProfiles.get(facts.country).domain_tlds

    @staticmethod
    def _is_downloaded_document(link: str) -> bool:
        """Whether a result is a document (a tender, a list of companies) where a number and an email sit side by side by chance."""
        path = urlparse(link).path.lower()
        return path.endswith(".pdf") or "/download/" in path

    @staticmethod
    def _is_legal_notice_of_a_website(line: SearchResultLine) -> bool:
        """Whether a result is the legal notice of a site that is no directory: the site of the number it shows."""
        if CandidateVerifier.is_known_third_party(line.link, line.host):
            return False
        return any(words in fold(line.text) for words in _LEGAL_NOTICE_WORDS)

    @staticmethod
    def _usable_emails(text: str, facts: CandidateFacts) -> list[str]:
        """Emails of a text that are well-formed and do not belong to a town hall, a directory or a platform."""
        ranked = email_candidate_scorer.rank_candidates(text, name=facts.name, city=facts.town)
        return [email for email, _ in ranked if validation_service.is_valid_email(email)]
