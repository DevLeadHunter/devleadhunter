"""
Detection of the contact tooling a prospect's website already offers.

The Réceptionniste IA pitch depends on it: a site that already runs a chat
widget (Tidio, Crisp, IONOS…) is "déjà équipé" — the pitch must change or the
prospect is skipped — and a contact form tells written requests already have a
door, just nobody answering it at 22h.

Only served HTML is read, no JavaScript runs: a widget injected by a tag
manager stays invisible. Small businesses paste the vendor snippet in their
page header, which is what this catches.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag
from sqlalchemy.orm import Session

from core.database import SessionLocal
from enums.chat_widget_provider import ChatWidgetProvider
from enums.website_status import WebsiteStatus
from models.prospect_db import ProspectDB
from services.website_liveness_service import WebsiteLivenessService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WebsiteEquipment:
    """Contact tooling found on a website."""

    chat_providers: tuple[ChatWidgetProvider, ...] = ()
    has_contact_form: bool = False

    @property
    def has_chat(self) -> bool:
        """True when at least one chat widget was detected."""
        return bool(self.chat_providers)

    def merged_with(self, other: WebsiteEquipment) -> WebsiteEquipment:
        """
        Combine the findings of two pages of the same site.

        Args:
            other: Findings of another page (typically the contact page).

        Returns:
            The union of both pages' chat providers and contact forms.
        """
        providers = tuple(dict.fromkeys((*self.chat_providers, *other.chat_providers)))
        return WebsiteEquipment(
            chat_providers=providers,
            has_contact_form=self.has_contact_form or other.has_contact_form,
        )


class WebsiteEquipmentDetector:
    """Finds chat widgets, contact forms and the contact page link in website HTML."""

    # Big pages are cut before parsing: vendor snippets and forms sit well within this.
    MAX_HTML_CHARS = 1_500_000

    # Lowercase substrings unique to each vendor's embed snippet (script host or global).
    CHAT_SIGNATURES: ClassVar[dict[ChatWidgetProvider, tuple[str, ...]]] = {
        ChatWidgetProvider.BOTPRESS: ("cdn.botpress.cloud/webchat", "botpresswebchat"),
        ChatWidgetProvider.BREVO: (
            "conversations-widget.brevo.com",
            "conversations-widget.sendinblue.com",
            "brevoconversations",
            "sibconversations",
        ),
        ChatWidgetProvider.CHATBASE: ("chatbase.co/embed",),
        ChatWidgetProvider.CHATRA: ("call.chatra.io", "chatraid"),
        ChatWidgetProvider.CHATWOOT: ("chatwootsdk",),
        ChatWidgetProvider.CHAPORT: ("app.chaport.com",),
        ChatWidgetProvider.CRISP: ("client.crisp.chat", "crisp_website_id"),
        ChatWidgetProvider.DRIFT: ("js.driftt.com",),
        ChatWidgetProvider.FRESHCHAT: ("wchat.freshchat.com", "fcwidget"),
        ChatWidgetProvider.GORGIAS: ("config.gorgias.chat",),
        # js.hs-scripts.com is HubSpot tracking, chat or not: only the messages host proves a chat.
        ChatWidgetProvider.HUBSPOT: ("js.usemessages.com",),
        ChatWidgetProvider.IADVIZE: ("halc.iadvize.com", "iadvize.com/iadvize.js"),
        ChatWidgetProvider.INTERCOM: ("widget.intercom.io", "js.intercomcdn.com", "intercomsettings"),
        # IONOS AI Receptionist web chat (ionos.ai-voice-receptionist.com/…/web-chat.js).
        ChatWidgetProvider.IONOS: ("ai-voice-receptionist.com",),
        ChatWidgetProvider.JIVOCHAT: ("code.jivosite.com", "code.jivo.chat"),
        ChatWidgetProvider.LANDBOT: ("cdn.landbot.io", "static.landbot.io"),
        ChatWidgetProvider.LIVECHAT: ("cdn.livechatinc.com",),
        ChatWidgetProvider.OLARK: ("static.olark.com",),
        ChatWidgetProvider.SMARTSUPP: ("smartsuppchat.com",),
        ChatWidgetProvider.TAWK: ("embed.tawk.to",),
        ChatWidgetProvider.TIDIO: ("code.tidio.co",),
        ChatWidgetProvider.TRENGO: ("widget.trengo.eu",),
        ChatWidgetProvider.USERLIKE: ("userlike-cdn-widgets",),
        ChatWidgetProvider.VOICEFLOW: ("cdn.voiceflow.com",),
        ChatWidgetProvider.ZENDESK: ("static.zdassets.com/ekr/snippet.js", "v2.zopim.com", "zesettings"),
        ChatWidgetProvider.ZOHO_SALESIQ: ("salesiq.zoho",),
    }

    # Form plugins and hosted form embeds. Their assets load site-wide, so a hit on the
    # home page means the site has a form somewhere — the level this signal is used at.
    FORM_PLUGIN_MARKERS: ClassVar[tuple[str, ...]] = (
        "wpcf7",
        "wpforms",
        "gform_wrapper",
        "elementor-form",
        "nf-form-cont",
        "frm_forms",
        "forminator-custom-form",
        "fluentform",
        "hsforms.net",
        "hbspt.forms",
        "embed.typeform.com",
        "tally.so/embed",
        "jotform.com/jsform",
        "form.jotform.com",
        "formspree.io",
        "getform.io",
    )

    # Contact page link hints, most specific first (FR / NL / DE / EN).
    CONTACT_LINK_HINTS: ClassVar[tuple[str, ...]] = ("contact", "kontakt", "devis", "offerte", "angebot", "quote")

    # A <form> carrying one of these in its id / class / action / name is not a contact form.
    NON_CONTACT_FORM_MARKERS: ClassVar[tuple[str, ...]] = (
        "newsletter",
        "subscribe",
        "mc-embedded",
        "mailchimp",
        "abonnement",
        "search",
        "recherche",
        "login",
        "connexion",
        "panier",
        "cart",
    )

    _TEXT_INPUT_TYPES: ClassVar[frozenset[str]] = frozenset({"", "text", "email", "tel"})
    _SEARCH_FIELD_NAMES: ClassVar[frozenset[str]] = frozenset({"s", "q", "search", "query", "recherche", "keyword"})

    @classmethod
    def detect(cls, html: str) -> WebsiteEquipment:
        """
        Detect the chat widgets and contact forms of one page.

        Args:
            html: Raw HTML as served.

        Returns:
            The page's contact tooling.
        """
        page = html[: cls.MAX_HTML_CHARS]
        return WebsiteEquipment(
            chat_providers=cls.detect_chat_providers(page),
            has_contact_form=cls.has_contact_form(page),
        )

    @classmethod
    def detect_chat_providers(cls, html: str) -> tuple[ChatWidgetProvider, ...]:
        """
        List the chat vendors whose embed snippet appears in the HTML.

        Args:
            html: Raw HTML as served.

        Returns:
            Detected vendors, in enum order (empty when none).
        """
        lowered = html.lower()
        return tuple(
            provider
            for provider, markers in cls.CHAT_SIGNATURES.items()
            if any(marker in lowered for marker in markers)
        )

    @classmethod
    def has_contact_form(cls, html: str) -> bool:
        """
        Whether the page carries a form a visitor can write to the business with.

        A known form plugin counts; otherwise a ``<form>`` qualifies when it has a
        message area, or an email / phone field among at least two text fields —
        search, newsletter, login and cart forms never do.

        Args:
            html: Raw HTML as served.

        Returns:
            True when a contact form is present.
        """
        lowered = html.lower()
        if any(marker in lowered for marker in cls.FORM_PLUGIN_MARKERS):
            return True
        if "<form" not in lowered:
            return False
        soup = BeautifulSoup(html, "html.parser")
        return any(cls._is_contact_form(form) for form in soup.find_all("form"))

    @classmethod
    def find_contact_page_url(cls, html: str, page_url: str) -> str | None:
        """
        Find the site's contact page among the page's same-site links.

        Args:
            html: Raw HTML of the page.
            page_url: URL the HTML was served from (resolves relative links).

        Returns:
            Absolute URL of the best contact-like link, or None when there is none.
        """
        soup = BeautifulSoup(html[: cls.MAX_HTML_CHARS], "html.parser")
        page_host = cls._site_host(page_url)
        best_url: str | None = None
        best_rank = len(cls.CONTACT_LINK_HINTS)
        for anchor in soup.find_all("a", href=True):
            href = str(anchor["href"]).strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            try:
                absolute = urljoin(page_url, href).split("#", 1)[0]
                parsed = urlparse(absolute)
                is_same_site = cls._site_host(absolute) == page_host
            except ValueError:
                # Malformed href (e.g. a broken IPv6 literal) — just not a usable link.
                continue
            if parsed.scheme not in ("http", "https") or not is_same_site:
                continue
            if absolute.rstrip("/") == page_url.split("#", 1)[0].rstrip("/"):
                continue
            haystack = f"{parsed.path} {anchor.get_text(' ', strip=True)}".lower()
            for rank, hint in enumerate(cls.CONTACT_LINK_HINTS[:best_rank]):
                if hint in haystack:
                    best_url, best_rank = absolute, rank
                    break
            if best_rank == 0:
                break
        return best_url

    @classmethod
    def _is_contact_form(cls, form: Tag) -> bool:
        """Apply the contact-form rule of :meth:`has_contact_form` to one ``<form>``."""
        identity = " ".join(
            " ".join(value) if isinstance(value, list) else str(value)
            for key in ("id", "class", "action", "name", "role")
            if (value := form.get(key))
        ).lower()
        if any(marker in identity for marker in cls.NON_CONTACT_FORM_MARKERS):
            return False

        inputs = form.find_all("input")
        types = [str(field.get("type") or "").lower() for field in inputs]
        names = {str(field.get("name") or "").lower() for field in inputs}
        if {"password", "search"} & set(types) or names & cls._SEARCH_FIELD_NAMES:
            return False
        if form.find("textarea") is not None:
            return True
        text_fields = [field_type for field_type in types if field_type in cls._TEXT_INPUT_TYPES]
        return bool({"email", "tel"} & set(types)) and len(text_fields) >= 2

    @staticmethod
    def _site_host(url: str) -> str:
        """Host of a URL without its ``www.`` prefix, for same-site comparisons."""
        host = (urlparse(url).hostname or "").lower()
        return host.removeprefix("www.")


class WebsiteEquipmentService:
    """Fetches prospects' websites and records the contact tooling they already have."""

    REQUEST_TIMEOUT_SECONDS = 8.0
    MAX_CONCURRENT_INSPECTIONS = 6

    # Verdicts of the liveness check that leave nothing to scan.
    _UNSCANNABLE_STATUSES: ClassVar[frozenset[str]] = frozenset(
        {WebsiteStatus.DEAD.value, WebsiteStatus.PLACEHOLDER.value}
    )

    def __init__(self) -> None:
        # Strong references: a fire-and-forget task nobody holds can be garbage-collected mid-run.
        self._background_tasks: set[asyncio.Task[None]] = set()

    @classmethod
    def is_scannable(cls, prospect: ProspectDB) -> bool:
        """
        Whether the prospect has a website worth scanning.

        Args:
            prospect: The prospect row.

        Returns:
            True for a URL not already known dead or a directory mini-site.
        """
        if not prospect.website or not prospect.website.strip():
            return False
        return prospect.website_status not in cls._UNSCANNABLE_STATUSES

    @staticmethod
    def to_snapshot(equipment: WebsiteEquipment) -> dict[str, list[str] | bool]:
        """
        Serialize findings for the ``prospects.website_equipment_json`` column.

        Args:
            equipment: Scan findings.

        Returns:
            ``{"chat_providers": [...], "has_contact_form": bool}``.
        """
        return {
            "chat_providers": [provider.value for provider in equipment.chat_providers],
            "has_contact_form": equipment.has_contact_form,
        }

    async def refresh_prospect(self, db: Session, prospect: ProspectDB) -> bool:
        """
        Scan one prospect's website now and store what was found.

        Args:
            db: Active database session (committed on success).
            prospect: A prospect with a scannable website.

        Returns:
            False when the site could not be read — the previous result is kept.
        """
        equipment = await self.inspect(prospect.website)
        if equipment is None:
            return False
        prospect.website_equipment_json = self.to_snapshot(equipment)
        prospect.website_equipment_at = datetime.utcnow()
        db.commit()
        return True

    def schedule_refresh(self, prospect_ids: list[int]) -> None:
        """
        Scan these prospects' websites in the background, without blocking the caller.

        Prospects without a scannable website are skipped at run time.

        Args:
            prospect_ids: Prospects to scan (typically those a search just saved).
        """
        if not prospect_ids:
            return
        task = asyncio.create_task(self._refresh_in_background(list(prospect_ids)))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _refresh_in_background(self, prospect_ids: list[int]) -> None:
        """Scan a batch on fresh sessions — none is held open while the sites are fetched."""
        db = SessionLocal()
        try:
            rows = db.query(ProspectDB).filter(ProspectDB.id.in_(prospect_ids)).all()
            website_by_id = {row.id: row.website for row in rows if self.is_scannable(row)}
        finally:
            db.close()
        if not website_by_id:
            return

        findings = await self.inspect_many([website for website in website_by_id.values() if website])

        db = SessionLocal()
        try:
            scanned_at = datetime.utcnow()
            for row in db.query(ProspectDB).filter(ProspectDB.id.in_(list(website_by_id))).all():
                website = website_by_id[row.id]
                equipment = findings.get(website) if website else None
                # Skip unreadable sites, and rows whose URL was edited while the scan ran.
                if equipment is None or row.website != website:
                    continue
                row.website_equipment_json = self.to_snapshot(equipment)
                row.website_equipment_at = scanned_at
            db.commit()
        except Exception:
            logger.exception("Website equipment scan could not be saved for %d prospect(s)", len(website_by_id))
            db.rollback()
        finally:
            db.close()

    async def inspect_many(self, websites: list[str]) -> dict[str, WebsiteEquipment | None]:
        """
        Inspect several websites concurrently, a few at a time.

        Args:
            websites: Website URLs (duplicates are inspected once).

        Returns:
            Each distinct URL mapped to its findings (None when unreadable).
        """
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_INSPECTIONS)

        async def bounded(website: str) -> WebsiteEquipment | None:
            async with semaphore:
                try:
                    return await self.inspect(website)
                except Exception:
                    # One odd site must not sink the whole batch.
                    logger.warning("Website equipment scan failed for %s", website, exc_info=True)
                    return None

        distinct = list(dict.fromkeys(websites))
        results = await asyncio.gather(*(bounded(website) for website in distinct))
        return dict(zip(distinct, results, strict=True))

    async def inspect(self, website: str | None) -> WebsiteEquipment | None:
        """
        Inspect the home page, then the contact page it links to.

        The contact page is read only when the home page shows no form: that is
        where small sites keep theirs, and it settles the question in one more
        request at most.

        Args:
            website: The prospect's website URL (scheme optional).

        Returns:
            The site's contact tooling, or None when there is no URL or the home
            page cannot be read (unknown, not "unequipped").
        """
        if not website or not website.strip():
            return None
        home_url = WebsiteLivenessService.normalize_url(website)
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.REQUEST_TIMEOUT_SECONDS,
            headers=WebsiteLivenessService.REQUEST_HEADERS,
        ) as client:
            home = await self._fetch_html(client, home_url)
            if home is None:
                return None
            served_url, home_html = home
            equipment = WebsiteEquipmentDetector.detect(home_html)
            if equipment.has_contact_form:
                return equipment
            contact_url = WebsiteEquipmentDetector.find_contact_page_url(home_html, served_url)
            if contact_url is None:
                return equipment
            contact = await self._fetch_html(client, contact_url)
            if contact is None:
                return equipment
            return equipment.merged_with(WebsiteEquipmentDetector.detect(contact[1]))

    @staticmethod
    async def _fetch_html(client: httpx.AsyncClient, url: str) -> tuple[str, str] | None:
        """
        GET a page and return its final URL and HTML.

        Args:
            client: Open HTTP client.
            url: Page to fetch.

        Returns:
            ``(final_url, html)``, or None on network error, non-2xx or non-HTML.
        """
        try:
            response = await client.get(url)
        except (httpx.HTTPError, httpx.InvalidURL, ValueError) as exc:
            logger.debug("Website equipment fetch failed for %s: %s", url, exc)
            return None
        content_type = response.headers.get("content-type", "").lower()
        if not response.is_success or ("html" not in content_type and content_type):
            return None
        return str(response.url), response.text


website_equipment_service = WebsiteEquipmentService()
