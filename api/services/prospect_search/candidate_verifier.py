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
import html
import json
import logging
import re
from typing import Any
from urllib.parse import unquote, urldefrag, urljoin, urlparse

import httpx

from enums.prospect_search import CandidateOrigin, EmailProofLevel
from enums.website_status import WebsiteStatus
from scrappers.brightdata_client import BrightDataClient
from scrappers.email_candidate_scoring import GENERIC_EMAIL_PROVIDERS, email_candidate_scorer
from scrappers.facebook_page_urls import FacebookPageUrl
from scrappers.google_result_link import GoogleResultLink
from scrappers.google_scraper import GoogleScraper
from services.decision_maker.normalize import company_similarity, company_tokens, fold
from services.prospect_search.business_name import COMMON_NAME_WORDS, NAME_LINK_WORDS, BusinessName
from services.prospect_search.candidate_facts import (
    BRAND_OUTLET_EVIDENCE_PREFIX,
    EMAIL_DOMAIN_SUBJECT,
    PRIVACY_PROXIED_DOMAIN_SUBJECT,
    CandidateFacts,
)
from services.prospect_search.candidate_identity import CandidateIdentity
from services.prospect_search.facebook_page_results import FacebookPageResults
from services.prospect_search.name_in_address import NameInAddress
from services.prospect_search.network_outlets import NetworkOutlets
from services.prospect_search.place_of_contact import PlaceOfContact
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

# Accented letters are accepted on both sides: a directory writes « garagemonçanense@bluewin.ch » after the
# business name, and cutting at the « ç » used to keep « anense@bluewin.ch », an address that bounces.
_EMAIL_RE: re.Pattern[str] = re.compile(r"[a-z0-9à-öø-ÿ._%+-]+@[a-z0-9à-öø-ÿ.-]+\.[a-z]{2,}", re.IGNORECASE)
_FEATURE_ID_RE: re.Pattern[str] = re.compile(r"0x[0-9a-f]+:0x([0-9a-f]+)", re.IGNORECASE)
_SWISS_COMPANY_NUMBER_RE: re.Pattern[str] = re.compile(r"CHE-\d{3}\.\d{3}\.\d{3}")
_SWISS_DIRECTORY_HOSTS: tuple[str, ...] = ("local.ch", "search.ch", "zip.ch")
_DOMAIN_IN_NAME_RE: re.Pattern[str] = re.compile(
    r"\b([a-z0-9][a-z0-9-]*\.(?:fr|ch|be|lu|ca|com|net|eu))\b", re.IGNORECASE
)
_STARRED_SWISS_NUMBER_RE: re.Pattern[str] = re.compile(r"(?:\+41|\b0)\s?\d{2}(?:[\s.]?\d){7}\s?\*")
_LABELLED_STARRED_NUMBER_RE: re.Pattern[str] = re.compile(
    r"(?:t[ée]l[ée]phone|mobile|portable|natel|fax)[^:;\d]{0,20}:\s*(?:\+41|0)\s?\d{2}(?:[\s.]?\d){7}\s?\*",
    re.IGNORECASE,
)
_NO_ADVERTISING_NOTICE_RE: re.Pattern[str] = re.compile(
    r"\*\s*(?:ne desire pas recevoir de publicite|ne souhaite pas de publicite|pas de publicite|keine werbung"
    r"|blocco pubblicita|no advertising)"
)
_HOUSE_NUMBER_RE: re.Pattern[str] = re.compile(r"(\d+)\s?[a-z]?$", re.IGNORECASE)
# What follows a Facebook page's name in a result's title (« Exemple Paysage | Facebook », « … - Accueil »).
_PAGE_TITLE_SEPARATOR_RE: re.Pattern[str] = re.compile(r"\s+[|·–—-]\s+")
# A word a page's name adds must be a word, not initials, to make another business.
_ADDED_WORD_MIN_CHARS: int = 4
# What the town reader answers for an address it cannot place.
_UNKNOWN_TOWN: str = "Inconnue"
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
# National numbers are nine digits after the trunk zero in France, Switzerland and Belgium.
_PHONE_DIGITS_COMPARED: int = 9
_DOMAIN_NAMED_AFTER_BUSINESS_SIMILARITY: float = 0.85
_OWN_DOMAIN_TIMEOUT_SECONDS: float = 8.0
_OWN_DOMAIN_READ_CHARS: int = 200_000
_LINK_RE: re.Pattern[str] = re.compile(
    r"<a\b[^>]*?\bhref=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL
)
_CONTACT_WORD: str = "contact"
# A name of one word is anybody's domain; a listing's tagline is nobody's.
_NAMED_DOMAIN_MIN_WORDS: int = 2
_NAMED_DOMAIN_MAX_WORDS: int = 4
_NAMED_DOMAIN_SUFFIXES: dict[str, tuple[str, ...]] = {
    "FR": ("fr", "com"),
    "CH": ("ch", "com"),
    "BE": ("be", "com"),
    "CA": ("ca", "com"),
}

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

        A network's outlet (its name or its category tells it), a Swiss business whose directory entry
        refuses advertising, a business whose card already leads to a live website: none is searched,
        each is ruled out. A number or an address Google reveals is looked up in the directory too.

        Args:
            facts: The candidate, completed in place.
            trade: Profile of the searched trade.
        """
        if self.mark_network_outlet(facts, trade):
            return
        contact_before_search = (facts.phone, facts.address)
        directory_entry = await self._find_swiss_directory_entry(facts, trade)
        if facts.refuses_advertising:
            return
        if facts.website is not None and await self._is_website_live(facts):
            return

        page = await self._client.google_parsed(f'"{facts.name}" {facts.town}'.strip(), country=facts.country)
        if page is None or self._shows_nothing(page):
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

        self._read_knowledge_panel(facts, page.get("knowledge"), trade)
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
        department = await PlaceOfContact.department_of(facts)
        self._keep_snippet_emails(facts, snippet_emails, results, verdict, trade, department=department)
        if (facts.phone, facts.address) != contact_before_search:
            directory_entry = await self._find_swiss_directory_entry(facts, trade) or directory_entry
        self._read_swiss_directory_entry(facts, directory_entry, trade)
        if facts.website is None and facts.has_website_button is not False:
            await self.consider_domains_named_after_business(facts, trade)

        if facts.website:
            status = await website_liveness_service.check_website_status(facts.website)
            facts.website_status = status.value if status is not None else None
        await self.consider_email_domain(facts, trade)
        await self.consider_email_source_site(facts, trade)
        await self.consider_privacy_proxied_domains(facts, trade)

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
        """Whether a result is a page of local.ch, search.ch or zip.ch (which copies them)."""
        return any(line.host == host or line.host.endswith(f".{host}") for host in _SWISS_DIRECTORY_HOSTS)

    @classmethod
    def read_no_advertising_mark(cls, facts: CandidateFacts, line: SearchResultLine) -> None:
        """
        Take the asterisk a Swiss directory prints after the numbers of a subscriber refusing advertising.

        A site copying the directory prints the notice instead (« * Ne désire pas recevoir de publicité »);
        an extract reached through a Google redirect keeps the directory's labels (« Numéro de téléphone
        mobile: 079 … * »).

        Args:
            facts: The candidate, completed in place.
            line: A result already known to be about the candidate.
        """
        if facts.country != "CH" or facts.refuses_advertising:
            return
        has_starred_number = (
            cls.is_swiss_directory_page(line) and _STARRED_SWISS_NUMBER_RE.search(line.description) is not None
        ) or _LABELLED_STARRED_NUMBER_RE.search(line.description) is not None
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
            entry_of_phone = await self._directory.entry_for_phone(facts.phone)
            entry = (
                entry_of_phone
                or await self._entry_found_by_name(facts, trade)
                or await self._entry_found_at_address(facts, trade)
            )
        except SwissDirectoryUnavailableError as exc:
            self.note_directory_unanswered(facts, exc)
            return None
        self.take_directory_asterisk(facts, entry)
        if entry_of_phone is None:
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
        logger.warning("Swiss directory unanswered for %s: %s", facts.name, error)
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
        for listed_entry in await self._directory.entries_for_name(
            BusinessName.without_legal_form(facts.name), facts.town
        ):
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
    def mark_brand_named_in_email(facts: CandidateFacts, trade: TradeProfile) -> None:
        """
        Mark the business as a brand's dealer when the words of its email open with the brand.

        « aixamautomobille@… » is an Aixam dealer's address: a brand in the email counts like a brand heading the
        name.

        Args:
            facts: The candidate, completed in place.
            trade: Profile of the searched trade, knowing the brands of its dealers.
        """
        if facts.email is None or facts.is_chain:
            return
        brand = trade.brand_named_in_address(facts.email.rpartition("@")[0])
        if brand is not None:
            facts.is_chain = True
            facts.add_evidence("chain", f"{BRAND_OUTLET_EVIDENCE_PREFIX}{brand}", source="Son email")

    @staticmethod
    def mark_network_outlet(facts: CandidateFacts, trade: TradeProfile, *, listing_name: str | None = None) -> bool:
        """
        Mark the business as a network's outlet when its name, its Facebook page or its listing shows a network.

        A brand's dealer is a network's outlet too.

        Args:
            facts: The candidate, completed in place.
            trade: Profile of the searched trade, knowing the brands of its dealers.
            listing_name: The name as the listing wrote it, tagline included (« Garage Exemple - Agent Renault »),
                when it is known; the business's name otherwise.

        Returns:
            Whether the business is a network's outlet.
        """
        name = listing_name or facts.name
        if NetworkOutlets.names_network(name):
            facts.is_chain = True
            facts.add_evidence("chain", name, source="Nom de l'enseigne")
            return True
        if NetworkOutlets.facebook_page_names_network(facts.facebook_url):
            facts.is_chain = True
            facts.add_evidence("chain", facts.facebook_url or "", source="Nom de sa page Facebook")
            return True
        brand = trade.brand_outlet_of(name, facts.google_category)
        if brand is None:
            return False
        facts.is_chain = True
        facts.add_evidence("chain", f"{BRAND_OUTLET_EVIDENCE_PREFIX}{brand}", source="Nom ou catégorie de la fiche")
        return True

    @staticmethod
    def result_lines(page: dict[str, Any]) -> list[SearchResultLine]:
        """The organic results of a parsed search page, as lines the rules and the judge read."""
        lines: list[SearchResultLine] = []
        for result in page.get("organic") or []:
            link = GoogleResultLink.address_of(result)
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
        return {token for token in cls.own_name_words(facts, trade) if len(token) >= 4}

    @classmethod
    def own_name_words(cls, facts: CandidateFacts, trade: TradeProfile) -> set[str]:
        """
        Words of the business name that belong to it alone: no linking word, trade word, common word, town or region
        (« Grand Est » names a page of any trade there).
        """
        trade_words = cls._trade_words(trade)
        place_words = company_tokens(facts.town) | BusinessName.region_words(facts.name)
        return {
            token
            for token in company_tokens(facts.name)
            if token not in NAME_LINK_WORDS
            and token not in COMMON_NAME_WORDS
            and token not in trade_words
            and token not in place_words
        }

    @staticmethod
    def _trade_words(trade: TradeProfile) -> set[str]:
        """Words a business name says its trade with (« garage », « paysagiste »)."""
        return {
            token
            for alias in (*trade.aliases, *trade.name_abbreviations, trade.label)
            for token in company_tokens(alias)
        }

    @classmethod
    def names_business(cls, text: str, facts: CandidateFacts, trade: TradeProfile) -> bool:
        """
        Whether a text talks about this business: close name, or every distinctive word present.

        A text carrying none of the words that belong to the name alone names another business,
        however close the rest (« Garage du Moulin » is not « Garage du Soleil »); a number the name
        carries besides its words (a département's « 66 ») tells nothing on its own.
        """
        own_words = cls.own_name_words(facts, trade)
        naming_words = {word for word in own_words if not word.isdigit()} or own_words
        text_words = company_tokens(text)
        if naming_words and not naming_words & text_words:
            return False
        if company_similarity(text, facts.name) >= _NAMED_IN_TEXT_SIMILARITY:
            return True
        distinctive = cls.distinctive_tokens(facts, trade)
        return bool(distinctive) and distinctive <= text_words

    @classmethod
    def is_facebook_page_of(cls, line: SearchResultLine, facts: CandidateFacts, trade: TradeProfile) -> bool:
        """
        Whether a Facebook result is this business's page, not a namesake's.

        A business named after its owner shares its name with strangers' personal
        profiles: the result must also place it in the town or in the trade. A page whose
        name puts another word in place of the business's trade (« La Taverne d'Odin » for
        « Les Jardins d'Odin ») is another business's, and so is a page placed elsewhere
        without the business's phone (« … | Le Marin Martinique » for a garage of Ducos).
        A listing without address must find its town or its number on the page: the trade
        alone fits every namesake of the trade (« Jardins Exemple » of Lyon for a listing
        searched from Metz).
        """
        if not cls.names_business(line.title, facts, trade) or cls._swaps_the_trade(line.title, facts, trade):
            return False
        if PlaceOfContact.names_another_place(line.text, facts) and not cls.shows_contact_of(line.text, facts):
            return False
        if not FacebookPageResults.is_page_root(line.link) and not cls._page_address_names_business(
            line.link, facts, trade
        ):
            return False
        if facts.is_placed_by_the_search_only:
            return facts.is_town_named_in(line.text) or cls.shows_contact_of(line.text, facts)
        text = fold(line.text)
        trade_words = (*trade.category_keywords, *trade.aliases)
        return facts.is_town_named_in(line.text) or any(fold(word) in text for word in trade_words)

    @staticmethod
    def _swaps_the_trade(title: str, facts: CandidateFacts, trade: TradeProfile) -> bool:
        """
        Whether a page's name drops the trade the business's name says and adds a word of its own.

        « La Taverne d'Odin » keeps « Odin » but says « taverne » where « Les Jardins d'Odin » says « jardins ».
        """
        page_name = _PAGE_TITLE_SEPARATOR_RE.split(title, maxsplit=1)[0]
        if not trade.names_trade(facts.name) or trade.names_trade(page_name):
            return False
        known_words = company_tokens(facts.name) | company_tokens(facts.town) | NAME_LINK_WORDS | COMMON_NAME_WORDS
        return any(len(word) >= _ADDED_WORD_MIN_CHARS and word not in known_words for word in company_tokens(page_name))

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

    def _read_knowledge_panel(self, facts: CandidateFacts, panel: Any, trade: TradeProfile) -> None:
        """
        Take the phone, address, rating, website and status of Google's panel when it is this business, the network
        its full name carries (« Garage Exemple | stop+go | … ») and the brand its presentation says it is approved
        by (« atelier … agréé Renault »). A listing's namesake has another Google identifier: its panel is the
        listing's only when it shows the listing's phone or town.
        """
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
        is_in_same_town = facts.is_town_named_in(panel_address)
        feature_id = _FEATURE_ID_RE.search(str(panel.get("fid") or ""))
        panel_cid = str(int(feature_id.group(1), 16)) if feature_id else None
        is_another_listing = panel_cid is not None and facts.google_cid is not None and panel_cid != facts.google_cid
        is_listing_itself = (
            facts.origin == CandidateOrigin.GOOGLE_LOCAL.value and has_same_name and not is_another_listing
        )
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
        if facts.city is None and panel_address:
            # A listing without a place took the searched town; the panel's address tells the real one.
            panel_town = GoogleScraper.extract_city(panel_address, facts.country)
            is_town_read = panel_town not in ("", _UNKNOWN_TOWN, panel_address)
            facts.city = panel_town if is_town_read else None
        if isinstance(panel.get("rating"), int | float):
            facts.google_rating = float(panel["rating"])
        if isinstance(panel.get("reviews_cnt"), int | float):
            facts.google_reviews_count = int(panel["reviews_cnt"])
        if panel_cid is not None and not facts.google_cid:
            facts.google_cid = panel_cid
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
        full_panel_name = str(panel.get("name") or "")
        if NetworkOutlets.names_network(full_panel_name):
            facts.is_chain = True
            facts.add_evidence("chain", full_panel_name, source="Fiche Google", url=maps_link or None)
        dealt_brand = trade.brand_dealt_in_text(str(panel.get("merchant_description") or ""))
        if dealt_brand is not None and facts.outlet_brand is None:
            facts.is_chain = True
            facts.add_evidence(
                "chain", f"{BRAND_OUTLET_EVIDENCE_PREFIX}{dealt_brand}", source="Présentation de sa fiche Google"
            )

    def _read_results(self, facts: CandidateFacts, results: list[SearchResultLine], trade: TradeProfile) -> bool:
        """
        Sort the results by rule: Facebook page, registry number, own website, a page of its network's or its brand's
        site naming it in its town (« garage.toyota.ch/exemple-develier »), a directory's title calling it a brand's
        agent (« Garage Exemple Agent Renault »).

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
            is_in_town = facts.is_town_named_in(line.text)
            is_named_there = is_in_town and self.names_business(line.title, facts, trade)
            if NetworkOutlets.is_network_page(line.link) and is_named_there:
                facts.is_chain = True
                facts.add_evidence("chain", line.host, source="Page de son réseau", url=line.link, snippet=line.text)
            brand = trade.brand_of_site(line.link)
            if brand is not None and is_named_there and facts.outlet_brand is None:
                facts.is_chain = True
                facts.add_evidence(
                    "chain",
                    f"{BRAND_OUTLET_EVIDENCE_PREFIX}{brand}",
                    source="Page du site de sa marque",
                    url=line.link,
                    snippet=line.text,
                )
            dealt_brand = (
                trade.brand_dealt_in_text(line.title) if self.names_business(line.title, facts, trade) else None
            )
            if dealt_brand is not None and facts.outlet_brand is None:
                facts.is_chain = True
                facts.add_evidence(
                    "chain", f"{BRAND_OUTLET_EVIDENCE_PREFIX}{dealt_brand}", source=line.host, url=line.link
                )
            if self.is_known_third_party(line.link, line.host):
                continue
            is_about_business = self.names_business(line.text, facts, trade)
            is_showing_its_contact = self.shows_contact_of(line.text, facts)
            is_host_spelling_its_name = NameInAddress.domain_names_business(line.host, facts)
            is_own_host = self._is_host_named_after(line.host, distinctive) or (
                is_host_spelling_its_name and (is_in_town or is_showing_its_contact)
            )
            if is_own_host and (is_about_business or is_showing_its_contact):
                self.consider_website(facts, line.link, source="Recherche Google", proof_url=line.link)
            elif is_about_business:
                has_unsettled_results = True
        return has_unsettled_results

    @classmethod
    def take_site_showing_contact(
        cls, facts: CandidateFacts, line: SearchResultLine, trade: TradeProfile, *, source: str
    ) -> None:
        """
        Take as the business's website a domain carrying its name whose page shows its phone or its email.

        Its contact page or legal notice publishes them (« garageexemple.fr/contact »), even when its Google listing
        declares only a Facebook page. A domain spelling its whole name beside a trade word counts even when its own
        word is short (« exemauto.fr » for Garage Exem'Auto).

        Args:
            facts: The candidate, completed in place.
            line: A result of one of its searches.
            trade: Profile of the searched trade.
            source: How the evidence names the search.
        """
        if cls.is_known_third_party(line.link, line.host) or not cls.shows_contact_of(line.text, facts):
            return
        is_host_named_after = cls._is_host_named_after(line.host, cls.distinctive_tokens(facts, trade))
        if is_host_named_after or NameInAddress.domain_names_business(line.host, facts):
            site = urlparse(line.link)
            cls.consider_website(facts, f"{site.scheme}://{site.netloc}/", source=source, proof_url=line.link)

    @classmethod
    def shows_contact_of(cls, text: str, facts: CandidateFacts) -> bool:
        """Whether a text shows the business's phone number, however spaced, or its email."""
        return cls.shows_phone_of(text, facts) or (bool(facts.email) and (facts.email or "") in text.lower())

    @staticmethod
    def shows_phone_of(text: str, facts: CandidateFacts) -> bool:
        """Whether a text shows the business's phone number, however spaced."""
        phone_digits = re.sub(r"\D", "", facts.phone or "")[-_PHONE_DIGITS_COMPARED:]
        return len(phone_digits) == _PHONE_DIGITS_COMPARED and phone_digits in re.sub(r"\D", "", text)

    @staticmethod
    def _is_host_named_after(host: str, distinctive: set[str]) -> bool:
        """Whether a host carries one of the business's distinctive words (« exemple » in « garagemexemple.fr »)."""
        compact_host = re.sub(r"[^a-z0-9]", "", host.rsplit(".", 1)[0])
        return any(len(token) >= _DISTINCTIVE_TOKEN_MIN_CHARS and token in compact_host for token in distinctive)

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
        """Whether a result sits on a social network, a directory, a registry, a booking platform or a network's site."""
        if validation_service.is_social_url(link) or validation_service.is_platform_url(link):
            return True
        if email_candidate_scorer.is_directory_host(host) or any(word in host for word in _COMPARISON_SITE_HOST_WORDS):
            return True
        if NetworkOutlets.is_network_page(link):
            return True
        return any(host == known or host.endswith(f".{known}") for known in _EXTRA_THIRD_PARTY_HOSTS)

    @classmethod
    def _shows_nothing(cls, page: dict[str, Any]) -> bool:
        """
        Whether a search page shows neither a result nor a panel: what Bright Data returns when Google failed.

        Such a page proves nothing about the business, a website least of all: the search is treated as unanswered.
        """
        return not cls.result_lines(page) and not page.get("knowledge")

    @classmethod
    def is_own_website(cls, website: str) -> bool:
        """Whether *website* can be the business's own site, not a social, platform, directory or network page."""
        host = (urlparse(website if "//" in website else f"//{website}").hostname or "").lower().removeprefix("www.")
        return validation_service.is_valid_website(website) and not cls.is_known_third_party(website, host)

    @classmethod
    def consider_website(cls, facts: CandidateFacts, website: str, *, source: str, proof_url: str) -> None:
        """
        Keep *website* as the business's own unless it is a social page, a platform or a directory.

        A page of a network's site (« www.motrio.fr/shop/… ») makes the business one of the network's outlets.
        """
        if validation_service.is_social_url(website):
            facebook_page = FacebookPageUrl.canonical(website)
            if facebook_page and facts.facebook_url is None:
                facts.facebook_url = facebook_page
                facts.add_evidence("facebook", facebook_page, source=source, url=proof_url)
            return
        if NetworkOutlets.is_network_page(website):
            facts.is_chain = True
            facts.add_evidence("chain", website, source=source, url=proof_url)
            return
        if not cls.is_own_website(website):
            return
        if facts.website is None:
            facts.website = website
            facts.add_evidence("website", website, source=source, url=proof_url)

    @classmethod
    async def consider_email_domain(cls, facts: CandidateFacts, trade: TradeProfile) -> None:
        """
        A business writing from its own domain may run a website there.

        Called each time an email is learnt (in the search results, by the contact search, on
        the Facebook page) and once more before a candidate is kept. The domain's front page
        counts as the business's website when it names the business, shows its phone, or the
        domain spells the business's name; a dead site or a directory mini-site known so far
        gives way to it. A live front page that does none of this is noted once: on a domain naming
        another business (« temoin-auto.ch »), the address is that business's and the email is
        forgotten; a group's address waits for a check. A domain spelling the business name
        that answers without showing its page (a bot check) is its website all the same; a parked
        domain only shows a dead site.

        Args:
            facts: The candidate, completed in place.
            trade: Profile of the searched trade.
        """
        if facts.email is None:
            return
        await cls._consider_business_domain(
            facts, facts.email.rsplit("@", 1)[-1], trade, subject=EMAIL_DOMAIN_SUBJECT, notes_unnamed_site=True
        )

    @classmethod
    async def consider_privacy_proxied_domains(cls, facts: CandidateFacts, trade: TradeProfile) -> None:
        """
        A domain a privacy service's address stands for is the business's own: its front page may be its website.

        The address itself is no email of the business (see ``note_privacy_proxied_domain``); the domain is read like
        the domain of its email, without noting a live page that does not name the business.

        Args:
            facts: The candidate, completed in place.
            trade: Profile of the searched trade.
        """
        for domain in facts.privacy_proxied_domains:
            await cls._consider_business_domain(
                facts, domain, trade, subject=PRIVACY_PROXIED_DOMAIN_SUBJECT, notes_unnamed_site=False
            )

    @staticmethod
    def note_privacy_proxied_domain(facts: CandidateFacts, email: str, line: SearchResultLine) -> None:
        """
        Record the domain a privacy service's address about the business stands for (« exemple.fr@domainsbyproxy.com »).

        Args:
            facts: The candidate, completed in place.
            email: The privacy service's address.
            line: The result showing it, already known to be about the business.
        """
        domain = email_candidate_scorer.domain_behind_privacy_proxy(email)
        if domain is None or domain in facts.privacy_proxied_domains:
            return
        facts.add_evidence("privacy_proxied_domain", domain, source=line.host, url=line.link, snippet=line.text)

    @staticmethod
    def note_website_technical_address(facts: CandidateFacts, email: str, line: SearchResultLine) -> None:
        """
        Record a site service's address a result gives the business (« aa@sentry.wixpress.com »): the page copied it
        from the business's own site, so the business has one.

        Args:
            facts: The candidate, completed in place.
            email: The site service's address.
            line: The result showing it, already known to be about the business.
        """
        if facts.website_technical_address is None:
            facts.add_evidence("website_technical_address", email, source=line.host, url=line.link, snippet=line.text)

    @classmethod
    def read_site_revealing_addresses(cls, facts: CandidateFacts, line: SearchResultLine) -> None:
        """
        Record what the addresses of a result reveal of the business's site: the domain a privacy service's address
        stands for, the site a site service's address was copied from.

        Args:
            facts: The candidate, completed in place.
            line: A result already known to be about the business.
        """
        for match in _EMAIL_RE.finditer(line.text):
            email = match.group(0).lower().rstrip(".")
            if email_candidate_scorer.is_privacy_proxy_address(email):
                cls.note_privacy_proxied_domain(facts, email, line)
            elif email_candidate_scorer.is_website_technical_address(email):
                cls.note_website_technical_address(facts, email, line)

    @classmethod
    async def _consider_business_domain(
        cls, facts: CandidateFacts, domain: str, trade: TradeProfile, *, subject: str, notes_unnamed_site: bool
    ) -> None:
        """
        Read the front page of a domain the business owns, and take it as its website when it is the business's.

        Args:
            facts: The candidate, completed in place.
            domain: The domain.
            trade: Profile of the searched trade.
            subject: How the evidence names the domain (« Le domaine de son email »).
            notes_unnamed_site: Whether a live page that does not name the business is noted, and the email written
                from a domain naming another business forgotten.
        """
        if facts.website_status == WebsiteStatus.LIVE.value:
            return
        if NetworkOutlets.is_network_page(domain):
            facts.is_chain = True
            facts.add_evidence("chain", domain, source=subject)
            return
        if domain in GENERIC_EMAIL_PROVIDERS or cls.is_known_third_party(f"https://{domain}", domain):
            return
        front_page = await cls._front_page_of(domain)
        is_named_after_business = cls._is_domain_named_after(domain, facts)
        if front_page is None:
            if is_named_after_business:
                await cls._take_domain_named_after_business(facts, domain, source=f"{subject} porte son nom")
            return
        page_url, page_text = front_page
        page_host = (urlparse(page_url).hostname or "").lower().removeprefix("www.")
        if not validation_service.is_valid_website(page_url) or cls.is_known_third_party(page_url, page_host):
            return
        phone_digits = re.sub(r"\D", "", facts.phone or "")[-8:]
        names_it = cls.names_business(page_text, facts, trade)
        shows_its_phone = len(phone_digits) == 8 and phone_digits in re.sub(r"\D", "", page_text)
        if not (names_it or shows_its_phone or is_named_after_business):
            is_site_already_noted = any(
                line.get("fact") == "email_domain_site" and line.get("value") == domain for line in facts.evidence
            )
            if notes_unnamed_site and not is_site_already_noted:
                if await website_liveness_service.check_website_status(page_url) == WebsiteStatus.LIVE:
                    facts.add_evidence("email_domain_site", domain, source=subject, url=page_url)
                    cls._drop_email_of_another_site(facts, domain)
            return
        status = await website_liveness_service.check_website_status(page_url)
        if facts.website is not None and status != WebsiteStatus.LIVE:
            return
        facts.website = page_url
        facts.website_status = status.value if status is not None else None
        facts.add_evidence("website", page_url, source=f"{subject} répond", url=page_url)

    @classmethod
    async def consider_domains_named_after_business(cls, facts: CandidateFacts, trade: TradeProfile) -> None:
        """
        Read the front page of the domains spelling the business's name, when no website is known and its listing may
        declare one (« espaces-verts-exemple.fr » for Espaces Verts Exemple).

        Google's results for the name may show only directories, and a page of local results read from the parsed JSON
        carries no « Site Web » button. A front page there is the business's website when it names the business and
        shows its number or its town, there or on the page its menu calls « Contact », where a small site often writes
        them alone: a namesake's site elsewhere does neither.

        Args:
            facts: The candidate, completed in place.
            trade: Profile of the searched trade.
        """
        for domain in cls.domains_named_after(facts, trade):
            front_page = await cls._front_page_of(domain)
            if front_page is None:
                continue
            page_url, page_text = front_page
            if not cls.names_business(page_text, facts, trade):
                continue
            shows_its_contact_or_town = cls.shows_contact_of(page_text, facts) or facts.is_town_named_in(page_text)
            if not shows_its_contact_or_town:
                contact_text = await cls._contact_page_text(page_url, page_text)
                shows_its_contact_or_town = cls.shows_contact_of(contact_text, facts) or facts.is_town_named_in(
                    contact_text
                )
            if not shows_its_contact_or_town:
                continue
            status = await website_liveness_service.check_website_status(page_url)
            facts.website = page_url
            facts.website_status = status.value if status is not None else None
            facts.add_evidence("website", page_url, source="Le domaine à son nom répond", url=page_url)
            return

    @classmethod
    def domains_named_after(cls, facts: CandidateFacts, trade: TradeProfile) -> list[str]:
        """
        The domains a business would register under its name, its country's first (« espaces-verts-exemple.fr »), with
        and without the trade word its name opens with (« exemauto.fr » for Garage Exem'Auto).

        A name without a word of its own (« Garage du Centre »), a single word or a listing's long tagline gives none.

        Args:
            facts: The business: its name and its country.
            trade: Profile of the searched trade.

        Returns:
            The domains, the words joined by hyphens, then glued.
        """
        if not {word for word in cls.own_name_words(facts, trade) if not word.isdigit()}:
            return []
        words = re.findall(r"[a-z0-9]+", fold(BusinessName.without_legal_form(facts.name)))
        spellings = [words, words[1:]] if words and words[0] in cls._trade_words(trade) else [words]
        labels = dict.fromkeys(
            label
            for spelling in spellings
            if _NAMED_DOMAIN_MIN_WORDS <= len(spelling) <= _NAMED_DOMAIN_MAX_WORDS
            for label in ("-".join(spelling), "".join(spelling))
        )
        return [
            f"{label}.{suffix}" for suffix in _NAMED_DOMAIN_SUFFIXES.get(facts.country, ("com",)) for label in labels
        ]

    @staticmethod
    def _drop_email_of_another_site(facts: CandidateFacts, domain: str) -> None:
        """
        Forget an email written from the domain of another business's live site (« info@temoin-auto.ch »).

        A group's domain (« groupe-exemple.ch ») may be the business's own mailbox: its email waits for a check.
        """
        if facts.email is None or facts.email.rsplit("@", 1)[-1] != domain:
            return
        if not NameInAddress.domain_names_another_business(domain, facts):
            return
        facts.add_evidence("email_dropped", facts.email, source=f"{domain} est le site en ligne d'une autre entreprise")
        facts.email = None
        facts.email_proof_level = None

    @staticmethod
    async def _take_domain_named_after_business(facts: CandidateFacts, domain: str, *, source: str) -> None:
        """Take as the business's website a domain spelling its name that answers, even behind a bot check."""
        page_url = f"https://{domain}/"
        if await website_liveness_service.check_website_status(page_url) != WebsiteStatus.LIVE:
            return
        facts.website = page_url
        facts.website_status = WebsiteStatus.LIVE.value
        facts.add_evidence("website", page_url, source=source, url=page_url)

    @staticmethod
    def _is_domain_named_after(domain: str, facts: CandidateFacts) -> bool:
        """
        Whether a domain spells the business name, give or take a letter, or its own words beside trade words.

        « bcp-paysagiste.com » is « Bcp Paysagistes »'s, « exemple-automobiles.fr » « SARL Exemple Automobiles
        Montluçon »'s, « ag-garage.fr » « AG Automobiles »'s.
        """
        compact_label = re.sub(r"[^a-z0-9]", "", fold(domain.rsplit(".", 1)[0]))
        compact_name = re.sub(r"[^a-z0-9]", "", fold(BusinessName.without_legal_form(facts.name)))
        similarity = difflib.SequenceMatcher(None, compact_label, compact_name).ratio()
        is_close_spelling = bool(compact_label) and similarity >= _DOMAIN_NAMED_AFTER_BUSINESS_SIMILARITY
        return is_close_spelling or NameInAddress.domain_names_business(domain, facts)

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
        """
        The final address and the first characters of a domain's front page, when it answers.

        A site whose certificate is broken still answers in plain HTTP: it is read there.
        """
        async with httpx.AsyncClient(
            timeout=_OWN_DOMAIN_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers=website_liveness_service.REQUEST_HEADERS,
        ) as http:
            for scheme in ("https", "http"):
                try:
                    response = await http.get(f"{scheme}://{domain}")
                except httpx.HTTPError:
                    continue
                if response.status_code != 200:
                    return None
                return str(response.url), response.text[:_OWN_DOMAIN_READ_CHARS]
        return None

    @staticmethod
    async def _contact_page_text(page_url: str, page_text: str) -> str:
        """
        The first characters of the page a site's front page links as its « Contact », on the same site.

        Args:
            page_url: The front page's final address.
            page_text: The front page's first characters.

        Returns:
            The contact page's first characters, or an empty text when the site links none or it does not answer.
        """
        site_host = (urlparse(page_url).hostname or "").removeprefix("www.")
        for match in _LINK_RE.finditer(page_text):
            link = urldefrag(urljoin(page_url, html.unescape(match.group(1)))).url
            label = re.sub(r"<[^>]+>", " ", match.group(2))
            is_same_site = (urlparse(link).hostname or "").removeprefix("www.") == site_host
            is_contact_link = _CONTACT_WORD in fold(f"{link} {label}")
            if not is_same_site or not is_contact_link or link.rstrip("/") == page_url.rstrip("/"):
                continue
            async with httpx.AsyncClient(
                timeout=_OWN_DOMAIN_TIMEOUT_SECONDS,
                follow_redirects=True,
                headers=website_liveness_service.REQUEST_HEADERS,
            ) as http:
                try:
                    response = await http.get(link)
                except httpx.HTTPError:
                    return ""
            return response.text[:_OWN_DOMAIN_READ_CHARS] if response.status_code == 200 else ""
        return ""

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
            if not self.is_about_another_business(line, facts, trade):
                facts.owner_name = verdict.owner_name
                facts.add_evidence("owner", verdict.owner_name, source=line.host, url=line.link, snippet=line.text)

    @staticmethod
    def _emails_in(results: list[SearchResultLine]) -> list[tuple[str, int]]:
        """Every email written in the results, with the index of its result."""
        found: list[tuple[str, int]] = []
        for index, line in enumerate(results):
            if CandidateVerifier.is_group_discussion(line.link) or PlaceOfContact.is_in_foreign_script(line.text):
                continue
            for match in _EMAIL_RE.finditer(email_candidate_scorer.without_glued_labels(line.text)):
                found.append((validation_service.ascii_email(match.group(0).lower().rstrip(".")), index))
        return found

    def _keep_snippet_emails(
        self,
        facts: CandidateFacts,
        snippet_emails: list[tuple[str, int]],
        results: list[SearchResultLine],
        verdict: JudgeVerdict | None,
        trade: TradeProfile,
        *,
        department: str | None,
    ) -> None:
        """
        Keep the emails the results give to this business, graded by how well the result proves it.

        A Facebook page about the business is its own; for a listing without address, only one naming its town or
        showing its contact (see :meth:`is_facebook_page_of`).
        """
        judged = {
            (entry.email, entry.result_index): entry.belongs_to_business
            for entry in (verdict.emails if verdict else [])
        }
        distinctive = self.distinctive_tokens(facts, trade)
        own_host = (urlparse(facts.website or "").hostname or "").lower().removeprefix("www.")
        for email, index in snippet_emails:
            line = results[index]
            if not validation_service.is_valid_email(email):
                continue
            is_about_business = self.names_business(line.title, facts, trade)
            is_given_by_judge = judged.get((email, index))
            if is_given_by_judge is False or (is_given_by_judge is None and not is_about_business):
                continue
            if email_candidate_scorer.is_privacy_proxy_address(email):
                self.note_privacy_proxied_domain(facts, email, line)
                continue
            if email_candidate_scorer.is_website_technical_address(email):
                self.note_website_technical_address(facts, email, line)
                continue
            if email_candidate_scorer.belongs_to_an_institution(email, city=facts.town):
                continue
            carries_name = any(token in email for token in distinctive if len(token) >= _DISTINCTIVE_TOKEN_MIN_CHARS)
            is_facebook_page = FacebookPageUrl.canonical(line.link) is not None
            if facts.is_placed_by_the_search_only:
                is_own_page = is_facebook_page and self.is_facebook_page_of(line, facts, trade)
            else:
                is_own_page = is_facebook_page and is_about_business
            is_directory_entry = self.is_known_third_party(line.link, line.host) and is_about_business
            proof = (
                EmailProofLevel.DIRECTORY
                if (is_own_page or is_directory_entry or carries_name)
                else EmailProofLevel.GUESSED
            )
            if not is_own_page:
                proof = self.grade_email_by_its_words(email, proof, facts)
            is_own_text = is_own_page or (bool(own_host) and line.host == own_host)
            self.offer_email_read_in(facts, email, proof, line, trade, department=department, is_own_text=is_own_text)

    @staticmethod
    def offer_email_read_in(
        facts: CandidateFacts,
        email: str,
        proof: EmailProofLevel,
        line: SearchResultLine,
        trade: TradeProfile,
        *,
        department: str | None,
        is_own_text: bool,
    ) -> None:
        """
        Offer an email read in a result, unless the result gives it to another business.

        A directory writes each business's number beside its address: an email nearest another number is that
        number's owner's, unless it spells the business's name (its manager's other number, a namesake: a person
        decides). A page about another business at another street (« Auto Exemple, Route des Ateliers 8 » for a
        garage of the Route de la Bourgeoisie) gives that business's email. A third party's page that does not place
        the business (its phone, its town, a postal code of its département) leaves the email unproven, whatever its
        words: a namesake elsewhere carries the same. A listing without address is placed by the searched town only:
        a page putting the business in another country or département gives a namesake's email, dropped. An email
        spelling the business's name, written beside its own number on a page naming it, is published by the
        business itself. The site's own address, read on its page about the business, is never the business's (see
        :meth:`is_publisher_address`).

        Args:
            facts: The candidate, completed in place.
            email: The address read.
            proof: How well the result proves the address is the business's.
            line: The result it was read in.
            trade: Profile of the searched trade.
            department: The business's French département, when known.
            is_own_text: Whether the result is the business's own page or site.
        """
        if not is_own_text and CandidateVerifier.is_publisher_address(email, line, facts, trade):
            return
        is_beside_another_phone = PlaceOfContact.is_beside_another_phone(line.text, email, facts.phone)
        if is_beside_another_phone and not CandidateVerifier.email_carries_name(email, facts, trade):
            return
        if not is_own_text and CandidateVerifier.is_about_another_business(line, facts, trade):
            return
        place_elsewhere = (
            PlaceOfContact.place_elsewhere_in(line.text, facts, department)
            if not is_own_text and facts.is_placed_by_the_search_only
            else None
        )
        if place_elsewhere is not None:
            facts.add_evidence(
                "email_dropped",
                email,
                source=f"La page qui le donne le place ailleurs ({place_elsewhere})",
                url=line.link,
            )
            return
        doubt: str | None = None
        if CandidateVerifier.is_published_beside_its_phone(email, line, facts, trade):
            proof = EmailProofLevel.PUBLISHED
        elif not is_own_text and is_beside_another_phone:
            doubt = "email_beside_another_phone"
        elif not is_own_text and not PlaceOfContact.shows_place_of(line.text, facts, department):
            doubt = "email_unplaced"
        if doubt is not None:
            proof = EmailProofLevel.GUESSED
        if facts.offer_email(email, proof, source=line.host, url=line.link, snippet=line.text) and doubt is not None:
            facts.add_evidence(doubt, email, source=line.host, url=line.link)

    @classmethod
    def is_publisher_address(
        cls, email: str, line: SearchResultLine, facts: CandidateFacts, trade: TradeProfile
    ) -> bool:
        """
        Whether an email is the address of the site a result comes from: its domain is the result's, a site that is
        neither the business's website nor named after it (« Email us: info@trouve-garage.ch » in the footer of
        a garage directory's page about the business).

        Args:
            email: The address read.
            line: The result it was read in.
            facts: The business, with its website when known.
            trade: Profile of the searched trade.

        Returns:
            True when the address is the site's own.
        """
        email_domain = email.rpartition("@")[2].lower()
        host = line.host
        is_same_site = bool(email_domain) and (
            host == email_domain or host.endswith(f".{email_domain}") or email_domain.endswith(f".{host}")
        )
        if not is_same_site:
            return False
        own_host = (urlparse(facts.website or "").hostname or "").lower().removeprefix("www.")
        is_named_after_business = NameInAddress.domain_names_business(host, facts) or cls._is_host_named_after(
            host, cls.distinctive_tokens(facts, trade)
        )
        return host != own_host and not is_named_after_business

    @classmethod
    def is_about_another_business(cls, line: SearchResultLine, facts: CandidateFacts, trade: TradeProfile) -> bool:
        """
        Whether a result is another business's entry: its title does not name the business, its words write another
        street than the business's (« AutoCentre Exemple SA, Rue des Gorges 2 » for a garage of the Rue du Moulin)
        and never its number.

        Args:
            line: A result of one of the business's searches.
            facts: The business, with its street address.
            trade: Profile of the searched trade.

        Returns:
            True when the result names another business living at another address.
        """
        return (
            not cls.names_business(line.title, facts, trade)
            and not cls.shows_phone_of(line.text, facts)
            and PlaceOfContact.shows_another_street(line.text, facts)
        )

    @classmethod
    def is_published_beside_its_phone(
        cls, email: str, line: SearchResultLine, facts: CandidateFacts, trade: TradeProfile
    ) -> bool:
        """
        Whether an email spelling the business's name is written beside its own number, on a page naming it.

        « Jules Exemple • Tél. 078 … • E-mail: jex.exemple@… » in a local bulletin: the same name and the same
        mobile as its listing make the address its own, wherever the page places it.

        Args:
            email: An address read in the result.
            line: The result.
            facts: The business, with its phone.
            trade: Profile of the searched trade.

        Returns:
            True when the number nearest the address is the business's and the page and the address both name it.
        """
        return (
            PlaceOfContact.is_beside_own_phone(line.text, email, facts.phone)
            and cls.names_business(line.text, facts, trade)
            and cls.email_carries_name(email, facts, trade)
        )

    @classmethod
    def email_carries_name(cls, email: str, facts: CandidateFacts, trade: TradeProfile) -> bool:
        """Whether an email spells the business's name, or carries one of its distinctive words (« bel.jaden@ »)."""
        local_part = email.rpartition("@")[0].lower()
        return NameInAddress.email_names_business(email, facts) or any(
            len(token) >= _DISTINCTIVE_TOKEN_MIN_CHARS and token in local_part
            for token in cls.distinctive_tokens(facts, trade)
        )

    @staticmethod
    def grade_email_by_its_words(email: str, proof: EmailProofLevel, facts: CandidateFacts) -> EmailProofLevel:
        """
        The proof a third party's email keeps once its own words are read.

        An address naming another business proves nothing, wherever it was read (« brd.auto.performance@… » on
        Garage Exemple's directory page); one spelling the business's own name proves at least as much as a
        directory (« gld-automobiles@… » for GLD Automobiles). The business's own page is not graded here.

        Args:
            email: The address found.
            proof: How well the page it was read on proves it belongs to the business.
            facts: The business.

        Returns:
            The proof to offer the email with.
        """
        if proof == EmailProofLevel.PUBLISHED:
            return proof
        if NameInAddress.email_names_another_business(email, facts):
            return EmailProofLevel.GUESSED
        if proof == EmailProofLevel.GUESSED and NameInAddress.email_names_business(email, facts):
            return EmailProofLevel.DIRECTORY
        return proof
