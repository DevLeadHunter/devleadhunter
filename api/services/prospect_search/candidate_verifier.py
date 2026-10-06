"""
Candidate verifier — one web search per business, read like an operator would.

The search « "name" town » answers what a listing alone cannot: does the business
own a website the listing does not show, is it closed for good, is it a chain, does
it have a Facebook page, is its email written somewhere. Known directories, registries
and social networks are sorted by rule; what the rules cannot settle goes to the
judge. Every fact kept carries the page it was read on.
"""

from __future__ import annotations

import difflib
import json
import logging
import re
from typing import Any
from urllib.parse import unquote, urlparse

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
from services.prospect_search.facebook_page_results import FacebookPageResults
from services.prospect_search.search_judge import JudgeVerdict, SearchJudge, SearchResultLine
from services.prospect_search.swiss_directory import (
    SwissDirectory,
    SwissDirectoryEntry,
    SwissDirectoryUnavailableError,
    swiss_directory,
)
from services.prospect_search.trade_catalog import TradeProfile
from services.validation_service import validation_service
from services.website_liveness_service import website_liveness_service

logger = logging.getLogger(__name__)

_EMAIL_RE: re.Pattern[str] = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", re.IGNORECASE)
_FEATURE_ID_RE: re.Pattern[str] = re.compile(r"0x[0-9a-f]+:0x([0-9a-f]+)", re.IGNORECASE)
_SWISS_COMPANY_NUMBER_RE: re.Pattern[str] = re.compile(r"CHE-\d{3}\.\d{3}\.\d{3}")
_SWISS_DIRECTORY_HOSTS: tuple[str, ...] = ("local.ch", "search.ch")
_LEGAL_FORM_RE: re.Pattern[str] = re.compile(
    r"(?<!\w)(s\.?\s?[aà]\.?\s?r\.?\s?l\.?|s\.?\s?a\.?|gmbh|ag|sagl|snc|eurl|sasu?|inc\.?|enr\.?|lt[ée]e)(?!\w)",
    re.IGNORECASE,
)
_DOMAIN_IN_NAME_RE: re.Pattern[str] = re.compile(
    r"\b([a-z0-9][a-z0-9-]*\.(?:fr|ch|be|lu|ca|com|net|eu))\b", re.IGNORECASE
)
_STARRED_SWISS_NUMBER_RE: re.Pattern[str] = re.compile(r"(?:\+41|\b0)\s?\d{2}(?:[\s.]?\d){7}\s?\*")
_NO_ADVERTISING_NOTICE_RE: re.Pattern[str] = re.compile(
    r"\*\s*(?:ne desire pas recevoir de publicite|ne souhaite pas de publicite|pas de publicite|keine werbung"
    r"|blocco pubblicita|no advertising)"
)
_HOUSE_NUMBER_RE: re.Pattern[str] = re.compile(r"(\d+)\s?[a-z]?$", re.IGNORECASE)
_ENTRY_HOUSE_NUMBER_RE: re.Pattern[str] = re.compile(r"/tel/[^/?]+/[a-z0-9-]*?-(\d+)[a-z]?/")
_LISTED_WEBSITE_RE: re.Pattern[str] = re.compile(
    r"(?:site web|site internet|website|webseite)\s*:\s*((?:https?://|www\.)[^\s;,]+)", re.IGNORECASE
)
_CLOSED_MARKERS: tuple[str, ...] = (
    "définitivement fermé",
    "fermé définitivement",
    "permanently closed",
    "fermé temporairement",
    "temporairement fermé",
    "temporarily closed",
)
_LIQUIDATION_WORDS_BY_REGISTER_MARKER: dict[str, str] = {
    "en liquidation": "en liquidation",
    "in liquidation": "en liquidation",
    "in auflosung": "en liquidation",
    "liquidation judiciaire": "en liquidation judiciaire",
    "societe radiee": "radiée",
    "entreprise radiee": "radiée",
}
_SAME_BUSINESS_SIMILARITY: float = 0.5
_NAMED_IN_TEXT_SIMILARITY: float = 0.4
_DISTINCTIVE_TOKEN_MIN_CHARS: int = 5
_DOMAIN_NAMED_AFTER_BUSINESS_SIMILARITY: float = 0.85
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

_COMPARISON_SITE_HOST_WORDS: tuple[str, ...] = ("comparatif", "vergleich", "comparison", "comparazione")
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
        "autoscout24.ch",
        "autoscout24.com",
        "motoscout24.ch",
        "garage-comparatif.ch",
        "garage-vergleich.ch",
        "garage-comparazione.ch",
        "garageromand.ch",
        "garagesuisse.com",
        "auto2day.ch",
        "cargpt.ch",
        "grip500reifen.ch",
        "pneus-online-suisse.ch",
        "centralepneus.ch",
        "firststop.ch",
        "bestdrive.ch",
        "electricien-comparatif.ch",
        "elektrikervergleich.ch",
        "nosavis.ch",
        "starofservice.ch",
        "guidefribourg.ch",
        "zip.ch",
        "1820.ch",
        "ranq.ch",
        "graph.swiss",
        "lixt.ch",
        "pappers.ch",
        "jobup.ch",
        "emploisuisse.com",
        "wa.me",
        "whatsapp.com",
        "t.me",
        "oeffnungszeitenbuch.de",
        "firmen.ch",
        "landi.ch",
        "autofit.ch",
        "411habitation.com",
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

    def __init__(
        self, client: BrightDataClient, judge: SearchJudge, directory: SwissDirectory = swiss_directory
    ) -> None:
        self._client = client
        self._judge = judge
        self._directory = directory
        self.judge_call_count: int = 0

    async def verify(self, facts: CandidateFacts, trade: TradeProfile) -> None:
        """
        Search the business by name and town, and write what the results prove into *facts*.

        A Swiss business whose directory entry refuses advertising is not searched, nor a business
        whose card already leads to a live website: either is ruled out. A number or an address
        Google reveals is looked up in the directory too.

        Args:
            facts: The candidate, completed in place.
            trade: Profile of the searched trade.
        """
        if self.is_chain_name(facts.name):
            facts.is_chain = True
            facts.add_evidence("chain", facts.name, source="Nom de l'enseigne")
            return
        contact_before_search = (facts.phone, facts.address)
        directory_entry = await self._find_swiss_directory_entry(facts, trade)
        if facts.refuses_advertising:
            return
        if facts.website is not None and await self._is_website_live(facts):
            return

        page = await self._client.google_parsed(f'"{facts.name}" {facts.town}'.strip(), country=facts.country)
        if page is None:
            return
        facts.is_verified = True
        domain_in_name = _DOMAIN_IN_NAME_RE.search(facts.name)
        if domain_in_name:
            self.consider_website(
                facts,
                f"https://{domain_in_name.group(1).lower()}/",
                source="Nom de la fiche Google",
                proof_url=facts.google_maps_url or f"https://{domain_in_name.group(1).lower()}/",
            )

        self._read_knowledge_panel(facts, page.get("knowledge"))
        results = self.result_lines(page)
        has_unsettled_results = self._read_results(facts, results, trade)
        self._read_swiss_directory_extracts(facts, results, trade)
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
        if (facts.phone, facts.address) != contact_before_search:
            directory_entry = await self._find_swiss_directory_entry(facts, trade) or directory_entry
        self._read_swiss_directory_entry(facts, directory_entry, trade)

        if facts.website:
            status = await website_liveness_service.check_website_status(facts.website)
            facts.website_status = status.value if status is not None else None
        await self.consider_email_domain(facts, trade)
        await self.consider_email_source_site(facts, trade)

    @staticmethod
    async def _is_website_live(facts: CandidateFacts) -> bool:
        """Check the website already known (the one the card's button leads to) and tell whether it is live."""
        status = await website_liveness_service.check_website_status(facts.website)
        facts.website_status = status.value if status is not None else None
        return status == WebsiteStatus.LIVE

    def _read_swiss_directory_extracts(
        self, facts: CandidateFacts, results: list[SearchResultLine], trade: TradeProfile
    ) -> None:
        """
        Read the local.ch and search.ch extracts about a Swiss business.

        They print an asterisk after the numbers of a subscriber who refuses advertising (sites
        copying them print the notice), and the website the directory lists (« Site web: www.… »).
        """
        if facts.country != "CH":
            return
        for line in results:
            if not self.names_business(line.title, facts, trade):
                continue
            self.read_no_advertising_mark(facts, line)
            if not self.is_swiss_directory_page(line):
                continue
            listed_website = _LISTED_WEBSITE_RE.search(line.description)
            if listed_website:
                self.consider_website(facts, listed_website.group(1).rstrip("."), source=line.host, proof_url=line.link)

    @staticmethod
    def is_swiss_directory_page(line: SearchResultLine) -> bool:
        """Whether a result is a page of local.ch or search.ch."""
        return any(line.host == host or line.host.endswith(f".{host}") for host in _SWISS_DIRECTORY_HOSTS)

    @classmethod
    def read_no_advertising_mark(cls, facts: CandidateFacts, line: SearchResultLine) -> None:
        """
        Take the asterisk a Swiss directory prints after the numbers of a subscriber refusing advertising.

        A site copying the directory prints the notice instead (« * Ne désire pas recevoir de publicité »).

        Args:
            facts: The candidate, completed in place.
            line: A result already known to be about the candidate.
        """
        if facts.country != "CH" or facts.refuses_advertising:
            return
        has_starred_number = (
            cls.is_swiss_directory_page(line) and _STARRED_SWISS_NUMBER_RE.search(line.description) is not None
        )
        if has_starred_number or _NO_ADVERTISING_NOTICE_RE.search(fold(line.text)):
            facts.refuses_advertising = True
            facts.add_evidence("no_advertising", "*", source=line.host, url=line.link, snippet=line.text)

    async def _find_swiss_directory_entry(
        self, facts: CandidateFacts, trade: TradeProfile
    ) -> SwissDirectoryEntry | None:
        """
        Find the search.ch entry of a Swiss business by its phone number, else by its name, else at its address.

        The asterisk refusing advertising belongs to the number, whoever the entry names: it is
        taken at once, before any paid search.
        """
        if facts.country != "CH" or not facts.matches_trade:
            return None
        try:
            entry = (
                await self._directory.entry_for_phone(facts.phone)
                or await self._entry_found_by_name(facts, trade)
                or await self._entry_found_at_address(facts, trade)
            )
        except SwissDirectoryUnavailableError as exc:
            self.note_directory_unanswered(facts, exc)
            return None
        self.take_directory_asterisk(facts, entry)
        if entry is None:
            self.take_zip_asterisk(facts, await self._directory.zip_listing_with_asterisk(facts.phone))
        return entry

    @staticmethod
    def take_directory_asterisk(facts: CandidateFacts, entry: SwissDirectoryEntry | None) -> None:
        """Mark the candidate as refusing advertising when its search.ch entry carries the asterisk."""
        if entry is not None and entry.refuses_advertising and not facts.refuses_advertising:
            facts.refuses_advertising = True
            facts.add_evidence("no_advertising", "*", source="Annuaire search.ch", url=entry.url)

    @staticmethod
    def take_zip_asterisk(facts: CandidateFacts, zip_page_url: str | None) -> None:
        """Mark the candidate as refusing advertising when zip.ch keeps the asterisk of a number search.ch dropped."""
        if zip_page_url is not None and not facts.refuses_advertising:
            facts.refuses_advertising = True
            facts.add_evidence("no_advertising", "*", source="zip.ch", url=zip_page_url)

    @staticmethod
    def note_directory_unanswered(facts: CandidateFacts, error: SwissDirectoryUnavailableError) -> None:
        """Record that search.ch did not answer, so the candidate's asterisk stays unread."""
        logger.info("Swiss directory unanswered for %s: %s", facts.name, error)
        facts.add_evidence("directory_unanswered", "search.ch", source="Annuaire search.ch")

    def _read_swiss_directory_entry(
        self, facts: CandidateFacts, entry: SwissDirectoryEntry | None, trade: TradeProfile
    ) -> None:
        """
        Take the website and the email a Swiss business's search.ch entry lists.

        They count only for a business entry, or an entry naming the business (never for a private
        person sharing the number), and never for a business the results already ruled out.
        """
        is_already_out = facts.is_closed or facts.is_chain or facts.is_other_business or not facts.matches_trade
        if entry is None or is_already_out:
            return
        if not (entry.is_business or self.names_business(entry.name, facts, trade)):
            return
        for website in entry.websites:
            self.consider_website(facts, website, source="Annuaire search.ch", proof_url=entry.url)
        for email in entry.emails:
            if validation_service.is_valid_email(email) and not email_candidate_scorer.belongs_to_an_institution(
                email, city=facts.town
            ):
                facts.offer_email(email, EmailProofLevel.DIRECTORY, source="Annuaire search.ch", url=entry.url)

    async def _entry_found_by_name(self, facts: CandidateFacts, trade: TradeProfile) -> SwissDirectoryEntry | None:
        """
        The entry of a Swiss business whose number the directory does not list, found by its name in its town.

        A business entry naming it, by its own name or by the owner on its extra line, is its entry;
        its page is read whole, since the list leaves out the asterisk of a second number.
        """
        name_without_legal_form = " ".join(_LEGAL_FORM_RE.sub(" ", facts.name).split()) or facts.name
        for listed_entry in await self._directory.entries_for_name(name_without_legal_form, facts.town):
            is_entry_of_business = listed_entry.is_business and self.names_business(
                f"{listed_entry.name} {listed_entry.extra_line}", facts, trade
            )
            if is_entry_of_business:
                return await self._directory.entry_at(listed_entry.url)
        return None

    async def _entry_found_at_address(self, facts: CandidateFacts, trade: TradeProfile) -> SwissDirectoryEntry | None:
        """
        The entry at the business's own address that carries its name, a sole trader's private entry included.

        Only the same house number counts, a namesake further down the street is someone else;
        the page is read whole, since the list leaves out the asterisk of a second number.
        """
        address = facts.address or ""
        house_number = _HOUSE_NUMBER_RE.search(address.split(",")[0].strip())
        name_words = sorted(self.distinctive_tokens(facts, trade), key=lambda word: (-len(word), word))
        if house_number is None or not name_words:
            return None
        for listed_entry in await self._directory.entries_at_address(name_words[0], address):
            entry_house_number = _ENTRY_HOUSE_NUMBER_RE.search(listed_entry.url)
            is_at_same_house = entry_house_number is None or entry_house_number.group(1) == house_number.group(1)
            if is_at_same_house and self.names_business(f"{listed_entry.name} {listed_entry.extra_line}", facts, trade):
                return await self._directory.entry_at(listed_entry.url)
        return None

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
        return bool(distinctive) and distinctive <= company_tokens(text)

    @classmethod
    def is_facebook_page_of(cls, line: SearchResultLine, facts: CandidateFacts, trade: TradeProfile) -> bool:
        """
        Whether a Facebook result is this business's page, not a namesake's.

        A business named after its owner shares its name with strangers' personal
        profiles: the result must also place it in the town or in the trade.
        """
        if not cls.names_business(line.title, facts, trade):
            return False
        if not FacebookPageResults.is_page_root(line.link) and not cls._page_address_names_business(
            line.link, facts, trade
        ):
            return False
        text = fold(line.text)
        is_in_town = bool(facts.town) and fold(facts.town) in text
        trade_words = (*trade.category_keywords, *trade.aliases)
        return is_in_town or any(fold(word) in text for word in trade_words)

    @classmethod
    def _page_address_names_business(cls, link: str, facts: CandidateFacts, trade: TradeProfile) -> bool:
        """Whether the page that published a Facebook post carries, in its address, a distinctive word of the business."""
        segments = [segment for segment in urlparse(link).path.split("/") if segment]
        if not segments:
            return False
        page_segment = segments[1] if len(segments) > 1 and segments[0] in {"p", "pages", "people"} else segments[0]
        compact_page_segment = re.sub(r"[^a-z0-9]", "", fold(unquote(page_segment)))
        return any(
            len(token) >= _DISTINCTIVE_TOKEN_MIN_CHARS and token in compact_page_segment
            for token in cls.distinctive_tokens(facts, trade)
        )

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
            self.consider_website(facts, site, source="Fiche Google", proof_url=maps_link or site)

    def _read_results(self, facts: CandidateFacts, results: list[SearchResultLine], trade: TradeProfile) -> bool:
        """
        Sort the results by rule: Facebook page, registry number, own website.

        Returns:
            Whether results naming the business remain on hosts the rules do not know.
        """
        distinctive = self.distinctive_tokens(facts, trade)
        has_unsettled_results = False
        for line in results:
            self._read_liquidation(facts, line, trade)
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
                self.consider_website(facts, line.link, source="Recherche Google", proof_url=line.link)
            else:
                has_unsettled_results = True
        return has_unsettled_results

    @classmethod
    def _read_liquidation(cls, facts: CandidateFacts, line: SearchResultLine, trade: TradeProfile) -> None:
        """Take a register's title naming the business « en liquidation » or struck off as its closing."""
        if facts.is_closed or not cls.names_business(line.title, facts, trade):
            return
        folded_title = fold(line.title)
        marker = next((marker for marker in _LIQUIDATION_WORDS_BY_REGISTER_MARKER if marker in folded_title), None)
        if marker:
            facts.is_closed = True
            facts.add_evidence(
                "closed",
                _LIQUIDATION_WORDS_BY_REGISTER_MARKER[marker],
                source=line.host,
                url=line.link,
                snippet=line.text,
            )

    @staticmethod
    def is_group_discussion(link: str) -> bool:
        """Whether a result is a post of a Facebook group, whose snippet mixes the comments of strangers."""
        return "facebook.com/groups/" in link.lower()

    @staticmethod
    def is_known_third_party(link: str, host: str) -> bool:
        """Whether a result sits on a social network, a directory, a registry or a booking platform."""
        if validation_service.is_social_url(link) or validation_service.is_platform_url(link):
            return True
        if email_candidate_scorer.is_directory_host(host) or any(word in host for word in _COMPARISON_SITE_HOST_WORDS):
            return True
        return any(host == known or host.endswith(f".{known}") for known in _EXTRA_THIRD_PARTY_HOSTS)

    @classmethod
    def consider_website(cls, facts: CandidateFacts, website: str, *, source: str, proof_url: str) -> None:
        """Keep *website* as the business's own unless it is a social page, a platform or a directory."""
        if validation_service.is_social_url(website):
            facebook_page = FacebookPageUrl.canonical(website)
            if facebook_page and facts.facebook_url is None:
                facts.facebook_url = facebook_page
                facts.add_evidence("facebook", facebook_page, source=source, url=proof_url)
            return
        parsed = urlparse(website if "//" in website else f"//{website}")
        host = (parsed.hostname or "").lower().removeprefix("www.")
        if not validation_service.is_valid_website(website) or cls.is_known_third_party(website, host):
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
        if not (names_it or shows_its_phone or cls._is_domain_named_after(domain, facts)):
            return
        status = await website_liveness_service.check_website_status(page_url)
        if facts.website is not None and status != WebsiteStatus.LIVE:
            return
        facts.website = page_url
        facts.website_status = status.value if status is not None else None
        facts.add_evidence("website", page_url, source="Le domaine de son email répond", url=page_url)

    @staticmethod
    def _is_domain_named_after(domain: str, facts: CandidateFacts) -> bool:
        """Whether a domain spells the business name, give or take a letter (« bcp-paysagiste.com » for « Bcp Paysagistes »)."""
        compact_label = re.sub(r"[^a-z0-9]", "", fold(domain.rsplit(".", 1)[0]))
        compact_name = re.sub(r"[^a-z0-9]", "", fold(_LEGAL_FORM_RE.sub(" ", facts.name)))
        similarity = difflib.SequenceMatcher(None, compact_label, compact_name).ratio()
        return bool(compact_label) and similarity >= _DOMAIN_NAMED_AFTER_BUSINESS_SIMILARITY

    @classmethod
    async def consider_email_source_site(cls, facts: CandidateFacts, trade: TradeProfile) -> None:
        """
        A site publishing the business's email under a name taken from that address is the business's own.

        « passion.paysage21@gmail.com » read on passion-paysage-dijon.fr makes that site its website; a town
        hall or a newspaper quoting the address is named otherwise and proves nothing.

        Args:
            facts: The candidate, completed in place.
            trade: Profile of the searched trade.
        """
        if facts.email is None or facts.website_status == WebsiteStatus.LIVE.value:
            return
        source_url = next(
            (
                line.get("url")
                for line in reversed(facts.evidence)
                if line.get("fact") == "email" and line.get("value") == facts.email and line.get("url")
            ),
            None,
        )
        if not source_url:
            return
        source = urlparse(source_url)
        host = (source.hostname or "").lower().removeprefix("www.")
        if not host or cls.is_known_third_party(source_url, host):
            return
        common_words = {
            token
            for word in (*trade.category_keywords, *trade.aliases, trade.label, facts.town)
            for token in re.split(r"[^a-z0-9]+", fold(word))
        }
        host_words = [
            word
            for word in re.split(r"[^a-z0-9]+", host.rsplit(".", 1)[0])
            if len(word) >= _DISTINCTIVE_TOKEN_MIN_CHARS and word not in common_words
        ]
        compact_local_part = re.sub(r"[^a-z0-9]", "", fold(facts.email.split("@", 1)[0]))
        if not any(word in compact_local_part for word in host_words):
            return
        site = f"{source.scheme}://{source.netloc}/"
        status = await website_liveness_service.check_website_status(site)
        if facts.website is not None and status != WebsiteStatus.LIVE:
            return
        facts.website = site
        facts.website_status = status.value if status is not None else None
        facts.add_evidence("website", site, source="Le site qui publie son email", url=source_url)

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
                self.consider_website(facts, line.link, source="Recherche Google (lu par l'IA)", proof_url=line.link)
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
            if CandidateVerifier.is_group_discussion(line.link):
                continue
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
