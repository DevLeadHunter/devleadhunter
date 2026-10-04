"""
Candidate verifier — one web search per business, read like an operator would.

The search « "name" town » answers what a listing alone cannot: does the business
own a website the listing does not show, is it closed for good, is it a chain, does
it have a Facebook page, is its email written somewhere. Known directories, registries
and social networks are sorted by rule; what the rules cannot settle goes to the
judge. Every fact kept carries the page it was read on.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from enums.prospect_search import CandidateOrigin, EmailProofLevel
from enums.website_status import WebsiteStatus
from scrappers.brightdata_client import BrightDataClient
from scrappers.email_candidate_scoring import GENERIC_EMAIL_PROVIDERS, email_candidate_scorer
from scrappers.facebook_page_urls import FacebookPageUrl
from services.decision_maker.normalize import company_similarity, company_tokens, fold
from services.prospect_search.business_name import BusinessName
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_identity import CandidateIdentity
from services.prospect_search.search_judge import JudgeVerdict, SearchJudge, SearchResultLine
from services.prospect_search.trade_catalog import TradeProfile
from services.validation_service import validation_service
from services.website_liveness_service import website_liveness_service

logger = logging.getLogger(__name__)

_EMAIL_RE: re.Pattern[str] = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", re.IGNORECASE)
_FEATURE_ID_RE: re.Pattern[str] = re.compile(r"0x[0-9a-f]+:0x([0-9a-f]+)", re.IGNORECASE)
_SWISS_COMPANY_NUMBER_RE: re.Pattern[str] = re.compile(r"CHE-\d{3}\.\d{3}\.\d{3}")
_CLOSED_MARKERS: tuple[str, ...] = (
    "définitivement fermé",
    "fermé définitivement",
    "permanently closed",
    "fermé temporairement",
    "temporairement fermé",
    "temporarily closed",
)
_SAME_BUSINESS_SIMILARITY: float = 0.5
_NAMED_IN_TEXT_SIMILARITY: float = 0.4
_DISTINCTIVE_TOKEN_MIN_CHARS: int = 5
_OWN_DOMAIN_TIMEOUT_SECONDS: float = 8.0
_OWN_DOMAIN_READ_CHARS: int = 200_000

# Words too common in business names to tell one business from another.
_COMMON_NAME_WORDS: frozenset[str] = frozenset(
    {
        "garage",
        "jardin",
        "jardins",
        "paysage",
        "paysages",
        "paysagiste",
        "service",
        "services",
        "entretien",
        "entreprise",
        "automobile",
        "automobiles",
        "plomberie",
        "chauffage",
        "sanitaire",
        "electricite",
        "electricien",
        "atelier",
        "artisan",
        "renovation",
        "travaux",
        "centre",
        "multiservices",
        "amenagement",
        "amenagements",
        "exterieurs",
    }
)

# Outlets of these networks are run by a group: the person reading the email does not decide.
_CHAIN_NAME_MARKERS: tuple[str, ...] = (
    "norauto",
    "midas",
    "speedy",
    "feu vert",
    "euromaster",
    "carglass",
    "roady",
    "jardiland",
    "gamm vert",
)
_NAME_WORD_SEPARATORS_RE: re.Pattern[str] = re.compile(r"[^a-z0-9]+")

# Directories, marketplaces and network sites missing from the shared blocklist. A garage's page on
# its network's site (AD, Motrio, a car brand…) is not its own website.
_EXTRA_THIRD_PARTY_HOSTS: frozenset[str] = frozenset(
    {
        "leboncoin.fr",
        "lacentrale.fr",
        "ad.fr",
        "motrio.fr",
        "motrio.com",
        "top-garage.fr",
        "precisium.fr",
        "eurorepar.fr",
        "boschcarservice.fr",
        "boschcarservice.com",
        "myautoconseil.com",
        "eurotyre.fr",
        "renault.fr",
        "citroen.fr",
        "peugeot.fr",
        "dacia.fr",
        "isuzu.fr",
        "qualit-enr.org",
        "handwerker.ch",
        "lozart.ch",
        "maptons.com",
        "gartenbau-liste.ch",
        "firmai.ch",
        "locaris.ch",
        "edirex.ch",
        "yellowpages.swiss",
        "artisanlocal.ch",
        "yoojo.ch",
        "yoojo.fr",
        "idgarages.com",
        "vroomly.com",
        "alentoor.fr",
        "jardin-et-paysagiste.fr",
        "pappers.fr",
        "annuaire-entreprises.data.gouv.fr",
        "manageo.fr",
        "northdata.com",
        "northdata.fr",
        "google.com",
        "waze.com",
        "linkedin.com",
        "tiktok.com",
        "youtube.com",
        "pinterest.com",
        "wikipedia.org",
    }
)


class CandidateVerifier:
    """Verifies one candidate with a single web search."""

    def __init__(self, client: BrightDataClient, judge: SearchJudge) -> None:
        self._client = client
        self._judge = judge
        self.judge_call_count: int = 0

    async def verify(self, facts: CandidateFacts, trade: TradeProfile) -> None:
        """
        Search the business by name and town, and write what the results prove into *facts*.

        Args:
            facts: The candidate, completed in place.
            trade: Profile of the searched trade.
        """
        if self.is_chain_name(facts.name):
            facts.is_chain = True
            facts.add_evidence("chain", facts.name, source="Nom de l'enseigne")
            return

        page = await self._client.google_parsed(f'"{facts.name}" {facts.town}'.strip(), country=facts.country)
        if page is None:
            return
        facts.is_verified = True

        self._read_knowledge_panel(facts, page.get("knowledge"))
        results = self.result_lines(page)
        has_unsettled_results = self._read_results(facts, results, trade)
        snippet_emails = self._emails_in(results)

        verdict: JudgeVerdict | None = None
        if (has_unsettled_results and facts.website is None) or snippet_emails:
            self.judge_call_count += 1
            verdict = await self._judge.judge(
                name=facts.name,
                city=facts.town,
                trade_label=trade.label,
                google_category=facts.google_category,
                results=results,
            )
        self._apply_verdict(facts, verdict, results, trade)
        self._keep_snippet_emails(facts, snippet_emails, results, verdict, trade)

        if facts.website:
            status = await website_liveness_service.check_website_status(facts.website)
            facts.website_status = status.value if status is not None else None
        await self.consider_email_domain(facts, trade)

    @staticmethod
    def is_chain_name(name: str) -> bool:
        """Whether a business name carries, as whole words, the name of a network run by a group."""
        name_words = f" {_NAME_WORD_SEPARATORS_RE.sub(' ', fold(name)).strip()} "
        return any(f" {marker} " in name_words for marker in _CHAIN_NAME_MARKERS)

    @staticmethod
    def result_lines(page: dict[str, Any]) -> list[SearchResultLine]:
        """The organic results of a parsed search page, as lines the rules and the judge read."""
        lines: list[SearchResultLine] = []
        for result in page.get("organic") or []:
            link = str(result.get("link") or "")
            if not link.startswith("http"):
                continue
            lines.append(
                SearchResultLine(
                    link=link,
                    host=(urlparse(link).hostname or "").lower().removeprefix("www."),
                    title=str(result.get("title") or ""),
                    description=str(result.get("description") or ""),
                )
            )
        return lines

    @classmethod
    def distinctive_tokens(cls, facts: CandidateFacts, trade: TradeProfile) -> set[str]:
        """Words of the business name that tell it from another of the same trade and town."""
        trade_words = {token for alias in (*trade.aliases, trade.label) for token in company_tokens(alias)}
        town_words = company_tokens(facts.town)
        return {
            token
            for token in company_tokens(facts.name)
            if len(token) >= 4
            and token not in _COMMON_NAME_WORDS
            and token not in trade_words
            and token not in town_words
        }

    @classmethod
    def names_business(cls, text: str, facts: CandidateFacts, trade: TradeProfile) -> bool:
        """Whether a text talks about this business: close name, or every distinctive word present."""
        if company_similarity(text, facts.name) >= _NAMED_IN_TEXT_SIMILARITY:
            return True
        distinctive = cls.distinctive_tokens(facts, trade)
        folded = fold(text)
        return bool(distinctive) and all(token in folded for token in distinctive)

    @classmethod
    def is_facebook_page_of(cls, line: SearchResultLine, facts: CandidateFacts, trade: TradeProfile) -> bool:
        """
        Whether a Facebook result is this business's page, not a namesake's.

        A business named after its owner shares its name with strangers' personal
        profiles: the result must also place it in the town or in the trade.
        """
        if not cls.names_business(line.title, facts, trade):
            return False
        text = fold(line.text)
        is_in_town = bool(facts.town) and fold(facts.town) in text
        trade_words = (*trade.category_keywords, *trade.aliases)
        return is_in_town or any(fold(word) in text for word in trade_words)

    @staticmethod
    def is_named_after(host: str, link: str, facts: CandidateFacts) -> bool:
        """
        Whether a page the judge calls the business's own website can be one.

        A directory lists a business under a path (« annuaire.org/entreprises/dupont »);
        a business's own site carries its name in the domain, or is the root of a domain.
        """
        compact_host = re.sub(r"[^a-z0-9]", "", host.rsplit(".", 1)[0])
        carries_name = any(len(token) >= 4 and token in compact_host for token in company_tokens(facts.name))
        path_segments = [segment for segment in urlparse(link).path.split("/") if segment]
        return carries_name or not path_segments

    def _read_knowledge_panel(self, facts: CandidateFacts, panel: Any) -> None:
        """Take the phone, address, rating, website and status of Google's panel when it is this business."""
        if not isinstance(panel, dict):
            return
        panel_phone = str(panel.get("phone") or "") or None
        candidate_phone_key = CandidateIdentity.phone_key(facts.phone, facts.country)
        has_same_phone = candidate_phone_key is not None and candidate_phone_key == CandidateIdentity.phone_key(
            panel_phone, facts.country
        )
        panel_name = BusinessName.clean(str(panel.get("name") or ""))
        has_same_name = company_similarity(panel_name, facts.name) >= _SAME_BUSINESS_SIMILARITY
        panel_address = str(panel.get("address") or "")
        is_in_same_town = bool(facts.town) and fold(facts.town) in fold(panel_address)
        is_listing_itself = facts.origin == CandidateOrigin.GOOGLE_LOCAL.value and has_same_name
        if not (has_same_phone or is_listing_itself or (has_same_name and is_in_same_town)):
            is_placed_in_another_town = bool(panel_address) and bool(facts.town) and not is_in_same_town
            if has_same_name and is_placed_in_another_town:
                facts.is_other_business = facts.origin != CandidateOrigin.GOOGLE_LOCAL.value
            return

        maps_link = str(panel.get("maps_link") or "")
        if facts.origin != CandidateOrigin.GOOGLE_LOCAL.value and has_same_name:
            # A registry writes the legal name in capitals: Google's spelling is the one customers know.
            facts.name = panel_name or facts.name
        facts.phone = facts.phone or panel_phone
        facts.address = facts.address or panel_address or None
        if isinstance(panel.get("rating"), int | float):
            facts.google_rating = float(panel["rating"])
        if isinstance(panel.get("reviews_cnt"), int | float):
            facts.google_reviews_count = int(panel["reviews_cnt"])
        feature_id = _FEATURE_ID_RE.search(str(panel.get("fid") or ""))
        if feature_id and not facts.google_cid:
            facts.google_cid = str(int(feature_id.group(1), 16))
            facts.google_maps_url = f"https://www.google.com/maps?cid={facts.google_cid}"
        summary = str(panel.get("summary") or panel.get("subtitle") or "")
        if summary and not facts.google_category:
            facts.google_category = summary.split(" à ", 1)[0].strip() or None

        panel_text = json.dumps(panel, ensure_ascii=False).lower()
        closed_marker = next((marker for marker in _CLOSED_MARKERS if marker in panel_text), None)
        if closed_marker:
            facts.is_closed = True
            facts.add_evidence("closed", closed_marker, source="Fiche Google", url=maps_link or None)
        site = str(panel.get("site") or "").strip()
        if site:
            self._consider_website(facts, site, source="Fiche Google", proof_url=maps_link or site)

    def _read_results(self, facts: CandidateFacts, results: list[SearchResultLine], trade: TradeProfile) -> bool:
        """
        Sort the results by rule: Facebook page, registry number, own website.

        Returns:
            Whether results naming the business remain on hosts the rules do not know.
        """
        distinctive = self.distinctive_tokens(facts, trade)
        has_unsettled_results = False
        for line in results:
            company_number = _SWISS_COMPANY_NUMBER_RE.search(line.text)
            if company_number and not facts.registry_number and self.names_business(line.text, facts, trade):
                facts.registry_number = company_number.group(0)
                facts.add_evidence("registry", facts.registry_number, source=line.host, url=line.link)

            facebook_page = FacebookPageUrl.canonical(line.link)
            if facebook_page:
                if facts.facebook_url is None and self.is_facebook_page_of(line, facts, trade):
                    facts.facebook_url = facebook_page
                    facts.add_evidence("facebook", facebook_page, source="Recherche Google", url=line.link)
                continue
            if self.is_known_third_party(line.link, line.host):
                continue
            if not self.names_business(line.text, facts, trade):
                continue
            compact_host = re.sub(r"[^a-z0-9]", "", line.host.rsplit(".", 1)[0])
            if any(len(token) >= _DISTINCTIVE_TOKEN_MIN_CHARS and token in compact_host for token in distinctive):
                self._consider_website(facts, line.link, source="Recherche Google", proof_url=line.link)
            else:
                has_unsettled_results = True
        return has_unsettled_results

    @staticmethod
    def is_known_third_party(link: str, host: str) -> bool:
        """Whether a result sits on a social network, a directory, a registry or a booking platform."""
        if validation_service.is_social_url(link) or validation_service.is_platform_url(link):
            return True
        if email_candidate_scorer.is_directory_host(host):
            return True
        return any(host == known or host.endswith(f".{known}") for known in _EXTRA_THIRD_PARTY_HOSTS)

    def _consider_website(self, facts: CandidateFacts, website: str, *, source: str, proof_url: str) -> None:
        """Keep *website* as the business's own unless it is a social page, a platform or a directory."""
        if validation_service.is_social_url(website):
            facebook_page = FacebookPageUrl.canonical(website)
            if facebook_page and facts.facebook_url is None:
                facts.facebook_url = facebook_page
                facts.add_evidence("facebook", facebook_page, source=source, url=proof_url)
            return
        parsed = urlparse(website if "//" in website else f"//{website}")
        host = (parsed.hostname or "").lower().removeprefix("www.")
        if not validation_service.is_valid_website(website) or self.is_known_third_party(website, host):
            return
        if facts.website is None:
            facts.website = website
            facts.add_evidence("website", website, source=source, url=proof_url)

    @classmethod
    async def consider_email_domain(cls, facts: CandidateFacts, trade: TradeProfile) -> None:
        """
        A business writing from its own domain may run a website there.

        Called each time an email is learnt: in the search results, by the contact search, on
        the Facebook page. The domain's front page counts as the business's website when it
        names the business or shows its phone; a dead site or a directory mini-site known so
        far gives way to it.

        Args:
            facts: The candidate, completed in place.
            trade: Profile of the searched trade.
        """
        if facts.email is None or facts.website_status == WebsiteStatus.LIVE.value:
            return
        domain = facts.email.rsplit("@", 1)[-1]
        if domain in GENERIC_EMAIL_PROVIDERS or cls.is_known_third_party(f"https://{domain}", domain):
            return
        front_page = await cls._front_page_of(domain)
        if front_page is None:
            return
        page_url, page_text = front_page
        page_host = (urlparse(page_url).hostname or "").lower().removeprefix("www.")
        if not validation_service.is_valid_website(page_url) or cls.is_known_third_party(page_url, page_host):
            return
        phone_digits = re.sub(r"\D", "", facts.phone or "")[-8:]
        names_it = cls.names_business(page_text, facts, trade)
        shows_its_phone = len(phone_digits) == 8 and phone_digits in re.sub(r"\D", "", page_text)
        if not (names_it or shows_its_phone):
            return
        status = await website_liveness_service.check_website_status(page_url)
        if facts.website is not None and status != WebsiteStatus.LIVE:
            return
        facts.website = page_url
        facts.website_status = status.value if status is not None else None
        facts.add_evidence("website", page_url, source="Le domaine de son email répond", url=page_url)

    @staticmethod
    async def _front_page_of(domain: str) -> tuple[str, str] | None:
        """The final address and the first characters of a domain's front page, when it answers."""
        try:
            async with httpx.AsyncClient(
                timeout=_OWN_DOMAIN_TIMEOUT_SECONDS,
                follow_redirects=True,
                headers=website_liveness_service.REQUEST_HEADERS,
            ) as http:
                response = await http.get(f"https://{domain}")
        except httpx.HTTPError:
            return None
        if response.status_code != 200:
            return None
        return str(response.url), response.text[:_OWN_DOMAIN_READ_CHARS]

    def _apply_verdict(
        self, facts: CandidateFacts, verdict: JudgeVerdict | None, results: list[SearchResultLine], trade: TradeProfile
    ) -> None:
        """Write the judge's reading into the facts, each answer with the result it points at."""
        if verdict is None:
            return
        if verdict.own_website_index is not None and facts.website is None:
            line = results[verdict.own_website_index]
            if self.is_named_after(line.host, line.link, facts):
                self._consider_website(facts, line.link, source="Recherche Google (lu par l'IA)", proof_url=line.link)
        if verdict.is_chain_or_franchise:
            facts.is_chain = True
            facts.add_evidence("chain", "franchise ou chaîne", source="Recherche Google (lu par l'IA)")
        if verdict.is_other_business and facts.origin != CandidateOrigin.GOOGLE_LOCAL.value:
            facts.is_other_business = True
        # Google's own category outranks the judge: only an unconfirmed trade can be denied.
        is_trade_confirmed = bool(facts.google_category) and not trade.is_generic
        if not verdict.matches_trade and not is_trade_confirmed:
            facts.matches_trade = False
        if verdict.owner_name and verdict.owner_name_index is not None and not facts.owner_name:
            line = results[verdict.owner_name_index]
            facts.owner_name = verdict.owner_name
            facts.add_evidence("owner", verdict.owner_name, source=line.host, url=line.link, snippet=line.text)

    @staticmethod
    def _emails_in(results: list[SearchResultLine]) -> list[tuple[str, int]]:
        """Every email written in the results, with the index of its result."""
        found: list[tuple[str, int]] = []
        for index, line in enumerate(results):
            for match in _EMAIL_RE.finditer(email_candidate_scorer.without_glued_labels(line.text)):
                found.append((match.group(0).lower().rstrip("."), index))
        return found

    def _keep_snippet_emails(
        self,
        facts: CandidateFacts,
        snippet_emails: list[tuple[str, int]],
        results: list[SearchResultLine],
        verdict: JudgeVerdict | None,
        trade: TradeProfile,
    ) -> None:
        """Keep the emails the results give to this business, graded by how well the result proves it."""
        judged = {
            (entry.email, entry.result_index): entry.belongs_to_business
            for entry in (verdict.emails if verdict else [])
        }
        distinctive = self.distinctive_tokens(facts, trade)
        for email, index in snippet_emails:
            line = results[index]
            if not validation_service.is_valid_email(email):
                continue
            if email_candidate_scorer.belongs_to_an_institution(email, city=facts.town):
                continue
            is_about_business = self.names_business(line.title, facts, trade)
            is_given_by_judge = judged.get((email, index))
            if is_given_by_judge is False or (is_given_by_judge is None and not is_about_business):
                continue
            carries_name = any(token in email for token in distinctive if len(token) >= _DISTINCTIVE_TOKEN_MIN_CHARS)
            is_own_page = FacebookPageUrl.canonical(line.link) is not None and is_about_business
            is_directory_entry = self.is_known_third_party(line.link, line.host) and is_about_business
            proof = (
                EmailProofLevel.DIRECTORY
                if (is_own_page or is_directory_entry or carries_name)
                else EmailProofLevel.GUESSED
            )
            facts.offer_email(email, proof, source=line.host, url=line.link, snippet=line.text)
