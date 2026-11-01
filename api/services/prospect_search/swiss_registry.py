"""
Swiss company register — the legal status the federal register (Zefix) gives a business.

A Swiss company « en liquidation » or struck off is closed, whatever its Google listing still
shows, and Google does not always show the register's page saying so. The register is read
only for a candidate about to be proposed: one request each.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from itertools import pairwise
from typing import Any
from urllib.parse import urlparse

import httpx

from services.country_profiles import CountryProfiles
from services.decision_maker.given_names import GivenNames
from services.decision_maker.normalize import fold, town_key
from services.decision_maker.swiss_register_people import RegisteredPerson, SwissRegisterPeople
from services.prospect_search.business_name import BusinessName
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.name_in_address import NameInAddress

logger = logging.getLogger(__name__)

_SEARCH_URL: str = "https://www.zefix.ch/ZefixREST/api/v1/firm/search.json"
_FIRM_URL: str = "https://www.zefix.ch/ZefixREST/api/v1/firm/{register_id}.json"
_UID_RE: re.Pattern[str] = re.compile(r"^CHE-\d{3}\.\d{3}\.\d{3}$")
_CANTON_SUFFIX_RE: re.Pattern[str] = re.compile(r"\s+[A-Z]{2}$")
_TIMEOUT_SECONDS: float = 15.0
_MAX_FIRMS: int = 10
_MAX_FIRMS_PER_WORD: int = 30
_MAX_SEARCHED_WORDS: int = 3
_MAX_ADDRESSES_READ: int = 5
_SOLE_PROPRIETORSHIP_FORM_ID: int = 1
_ACTIVE_STATUS: str = "EXISTIEREND"
_IN_LIQUIDATION_STATUS: str = "IN_AUFLOESUNG"
_STRUCK_OFF_STATUS: str = "GELOESCHT"
# An old striking off may hide a tradesperson who carries on in another form; a recent one is a closing.
_RECENT_STRIKING_OFF: timedelta = timedelta(days=3 * 365)
_LIQUIDATION_SUFFIX_RE: re.Pattern[str] = re.compile(
    r",?\s*(?:en liquidation|in liquidation|in liquidazione)\s*$", re.IGNORECASE
)
_HONORIFIC_RE: re.Pattern[str] = re.compile(r"^\s*(?:mr|mrs|mme|m|monsieur|madame|herr|frau)\.?\s+", re.IGNORECASE)
_REGISTER_SOURCE: str = "Registre du commerce (Zefix)"
_OTHER_ADDRESS_RE: re.Pattern[str] = re.compile(
    r"(?:Autre adresse|Weitere Adresse|Altro indirizzo)\s*:\s*[^.;]*?\b(\d{4})\s+([^.,;]+)", re.IGNORECASE
)
_INITIALS_TOKEN_RE: re.Pattern[str] = re.compile(r"^[A-Z]{2,3}$")
_FIRM_NAME_PART_SEPARATOR_RE: re.Pattern[str] = re.compile(r"\s*,\s*|\s+[-–]\s+")
# The cantonal excerpts of Vaud, Geneva, Fribourg and Neuchâtel (« …/extract?companyOfsUid=CHE-… »), and their request.
_EXCERPT_PATH: str = "/extract"
_XSRF_COOKIE: str = "XSRF-TOKEN"
_EXCERPT_REQUEST: dict[str, Any] = {
    "rcentId": None,
    "lng": "FR",
    "rad": True,
    "companyOfrcId13": None,
    "extraitTravail": False,
    "admOrderDirection": "ASC",
    "order": None,
}


@dataclass(frozen=True)
class SwissRegisterFirm:
    """A firm as the federal register lists it."""

    name: str
    seat: str
    status: str
    uid: str
    struck_off_on: date | None = None
    register_id: int | None = None
    legal_form_id: int | None = None

    @property
    def is_sole_proprietorship(self) -> bool:
        """Whether the firm is a sole proprietorship (« entreprise individuelle »), whose name holds its owner's."""
        return self.legal_form_id == _SOLE_PROPRIETORSHIP_FORM_ID


class SwissRegistry:
    """Reads the federal company register for the closing of a Swiss business."""

    async def read_closing(self, facts: CandidateFacts) -> None:
        """
        Take the register's « en liquidation » or recent « radiée » as the closing of a Swiss company.

        The firm of the company number the search read is the business, wherever it sits (« Exemple Jardinier »
        filed at Cornaux for a listing of Le Landeron); without a number, only a firm of its name (legal form,
        civility and trade words aside) at its seat or at its postal code counts (a commune merged into another
        keeps its postal code). An active one clears the business, and gives its company number when it has none.

        Args:
            facts: The candidate, completed in place.
        """
        uid = facts.registry_number if _UID_RE.match(facts.registry_number or "") else None
        if facts.country != "CH" or facts.is_closed or not (uid or facts.town):
            return
        firm = await self.firm_of(
            name=facts.name, town=facts.town, uid=uid, postal_code=self.postal_code_of(facts.address)
        )
        if firm is None:
            if uid is None:
                await self._read_closed_firm_holding_name(facts)
            return
        if firm.status == _ACTIVE_STATUS:
            if not facts.registry_number and firm.uid:
                facts.registry_number = firm.uid
                facts.add_evidence("registry", firm.uid, source=_REGISTER_SOURCE)
            return
        closing = self.closing_words(firm)
        if closing is not None:
            facts.is_closed = True
            facts.add_evidence("closed", closing, source=_REGISTER_SOURCE)

    async def _read_closed_firm_holding_name(self, facts: CandidateFacts) -> None:
        """
        Take a closed firm whose name holds the business's whole name, at its place, as the business's firm.

        The register adds its owner's name to a sole proprietorship (« CENTRE AUTO EXEMPLE MODELE » for
        « CENTRE AUTO EXEMPLE »): in liquidation or struck off lately there, it closes the business — unless an
        active firm of the business's words sits at its place (« EXEMPLE SWISS SA », founded next door the month
        the old one went bankrupt), when the business may go on under it and a person checks.

        Args:
            facts: The candidate, completed in place.
        """
        if not BusinessName.distinctive_stems(facts.name):
            return
        postal_code = self.postal_code_of(facts.address)
        name_words = self._words(self.register_name(facts.name))
        closed_holders = [
            firm
            for firm in await self.firms_named(self.name_inside(facts.name), max_entries=_MAX_FIRMS_PER_WORD)
            if self.closing_words(firm) is not None
            and name_words <= self._words(_LIQUIDATION_SUFFIX_RE.sub("", firm.name))
        ]
        holder = next(iter(await self._firms_at_place(closed_holders, town=facts.town, postal_code=postal_code)), None)
        closing = self.closing_words(holder) if holder is not None else None
        if holder is None or closing is None:
            return
        successor = await self.firm_by_words_and_address(name=facts.name, town=facts.town, postal_code=postal_code)
        if successor is not None:
            facts.add_evidence(
                "register_successor", successor.name, source=_REGISTER_SOURCE, snippet=f"{holder.name}, {closing}"
            )
            return
        facts.is_closed = True
        facts.add_evidence("closed", closing, source=_REGISTER_SOURCE, snippet=holder.name)

    async def note_email_firm_elsewhere(self, facts: CandidateFacts) -> None:
        """
        Note where the register seats the firm a Swiss business's email names, when it is not the business's place.

        « garageexemple@ » read on a page a search found, for a « Garage de la Gare » of one town: the register has
        « Garage de la Gare Jules Exemple S.A. » eighty kilometres away and no Exemple firm in the business's town,
        so the page and its email are a namesake's. A first name says nothing: many firms bear it.

        Args:
            facts: The candidate, completed in place.
        """
        if facts.country != "CH" or facts.email is None or facts.contact_elsewhere is not None:
            return
        postal_code = self.postal_code_of(facts.address)
        for word in NameInAddress.foreign_name_words(facts.email, facts)[:_MAX_SEARCHED_WORDS]:
            if GivenNames.is_common_given_name(word):
                continue
            holders = [
                firm
                for firm in await self.firms_named(word, max_entries=_MAX_FIRMS_PER_WORD)
                if word in self._words(firm.name)
            ]
            if not holders or await self._firms_at_place(holders, town=facts.town, postal_code=postal_code):
                continue
            namesake = next(
                (firm for firm in holders if self.shares_words(firm.name, facts.name, town=facts.town)), None
            )
            if namesake is not None:
                facts.add_evidence(
                    "contact_elsewhere",
                    f"{namesake.seat}, où le registre inscrit « {namesake.name} »",
                    source="Son email",
                )
                return

    @staticmethod
    def postal_code_of(address: str | None) -> str | None:
        """The four-digit postal code a Swiss address writes (« Rte Exemple 5, 1564 Domdidier »), if any."""
        postal_match = CountryProfiles.get("CH").postal_code_regex.search(address or "")
        return postal_match.group(1) if postal_match else None

    async def firms_named(self, name: str, *, max_entries: int = _MAX_FIRMS) -> list[SwissRegisterFirm]:
        """
        The firms whose name contains *name*, struck off ones included, as the register lists them.

        Args:
            name: The business name, without its legal form nor civility.
            max_entries: How many firms the register returns at most.

        Returns:
            The firms; empty when the register lists none or does not answer.
        """
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http:
                response = await http.post(
                    _SEARCH_URL,
                    json={"name": name, "languageKey": "fr", "maxEntries": max_entries, "deletedFirms": True},
                )
        except httpx.HTTPError as exc:
            logger.warning("Zefix lookup of %s failed: %s", name, exc)
            return []
        if response.status_code != 200:
            return []
        return [
            SwissRegisterFirm(
                name=str(firm.get("name") or ""),
                seat=str(firm.get("legalSeat") or ""),
                status=str(firm.get("status") or ""),
                uid=str(firm.get("uidFormatted") or ""),
                struck_off_on=date.fromisoformat(firm["deleteDate"]) if firm.get("deleteDate") else None,
                register_id=int(firm["ehraid"]) if str(firm.get("ehraid") or "").isdigit() else None,
                legal_form_id=int(firm["legalFormId"]) if str(firm.get("legalFormId") or "").isdigit() else None,
            )
            for firm in response.json().get("list") or []
        ]

    async def firm_of(
        self,
        *,
        name: str,
        town: str | None,
        uid: str | None = None,
        postal_code: str | None = None,
        allow_unique_name: bool = False,
    ) -> SwissRegisterFirm | None:
        """
        The register's firm for a business: the one of its company number, else the one of its name at its seat.

        The name is the business's, legal form and civility aside, or its words beside a trade word the register
        adds (« Garage Exemple Jules » for « Exemple Jules »). A commune merged into another files its firms under
        the new commune (« Belmont-Broye » for Domdidier): a firm of the name whose registered address has the
        business's postal code is it. A business works in a village while its firm sits in the commune (« Le
        Châble », seat « Val de Bagnes »): with ``allow_unique_name``, the only active firm of that name in
        Switzerland is it too. The register finds a firm by the start of its name: one naming its owner first
        (« Jules Modèle, Garage du Lac ») is searched with the name inside it when no firm starting with the name
        sits there.

        Args:
            name: The business name.
            town: The business's town, the seat a name match must share.
            uid: Its company number (« CHE-123.456.789 ») when the search read one.
            postal_code: The business's postal code, the registered address of a firm sitting elsewhere must share.
            allow_unique_name: Whether the single active firm of the name counts away from the seat.

        Returns:
            The firm, an active one first when several match; ``None`` when the register lists none.
        """
        if uid and _UID_RE.match(uid):
            firms = [firm for firm in await self.firms_named(uid) if firm.uid == uid]
        else:
            named = [
                firm for firm in await self.firms_named(self.register_name(name)) if self.is_named_like(firm.name, name)
            ]
            firms = await self._firms_at_place(named, town=town, postal_code=postal_code)
            if not firms:
                named_inside = [
                    firm
                    for firm in await self.firms_named(self.name_inside(name), max_entries=_MAX_FIRMS_PER_WORD)
                    if self.is_named_like(firm.name, name) and firm not in named
                ]
                named = [*named, *named_inside]
                firms = await self._firms_at_place(named_inside, town=town, postal_code=postal_code)
            active_named = [firm for firm in named if firm.status == _ACTIVE_STATUS]
            if not firms and allow_unique_name and len(active_named) == 1:
                firms = active_named
        return next((firm for firm in firms if firm.status == _ACTIVE_STATUS), firms[0] if firms else None)

    async def _firms_at_place(
        self, firms: list[SwissRegisterFirm], *, town: str | None, postal_code: str | None
    ) -> list[SwissRegisterFirm]:
        """The firms seated in the business's town, else those whose registered address has its postal code."""
        at_seat = [firm for firm in firms if town and fold(firm.seat) == fold(town)]
        if at_seat or not postal_code:
            return at_seat
        return [firm for firm in firms[:_MAX_ADDRESSES_READ] if (await self.address_of(firm))[0] == postal_code]

    @classmethod
    def name_inside(cls, name: str) -> str:
        """The register's query for firms holding a business name anywhere in theirs (« *Garage du Lac »)."""
        return f"*{cls.register_name(name)}"

    @classmethod
    def is_named_like(cls, firm_name: str, name: str) -> bool:
        """
        Whether a firm bears a business's name: the same letters, legal form, civility and « en liquidation » aside,
        or one name holding all the other's words, the same distinctive ones and a trade word more (« Garage Exemple
        Jules » for « Exemple Jules »). « Exemple Carrosserie » does not bear « Exemple Auto », a garage of the same
        family. A sole proprietorship sets its owner beside its name, before or after a comma (« Jules Modèle,
        Garage du Lac », « Garage du Lac, Modèle »): one part bearing the name is enough.

        Args:
            firm_name: The firm's name in the register.
            name: The business name.

        Returns:
            True when the firm bears the name.
        """
        parts = [part for part in _FIRM_NAME_PART_SEPARATOR_RE.split(firm_name) if part.strip()]
        return any(cls._bears_name(part, name) for part in dict.fromkeys([firm_name, *parts]))

    @classmethod
    def _bears_name(cls, firm_name: str, name: str) -> bool:
        """Whether a firm's name, or one of its parts, bears a business's name (see :meth:`is_named_like`)."""
        if cls._compact(firm_name) == cls._compact(name):
            return True
        firm_name = cls.register_name(_LIQUIDATION_SUFFIX_RE.sub("", firm_name))
        name = cls.register_name(name)
        firm_words, words = cls._words(firm_name), cls._words(name)
        distinctive = BusinessName.distinctive_stems(name)
        return (
            (firm_words <= words or words <= firm_words)
            and bool(distinctive)
            and BusinessName.distinctive_stems(firm_name) == distinctive
        )

    @staticmethod
    def _words(name: str) -> set[str]:
        """The folded words of a name."""
        return set(re.findall(r"[a-z0-9]+", fold(name)))

    async def firm_by_words_and_address(
        self, *, name: str, town: str | None, postal_code: str | None
    ) -> SwissRegisterFirm | None:
        """
        The active firm the register files a business under another name, found by its words at the business's address.

        The register spells a name its own way: the owner's name added (« Exemple Mécanique Modèle » for
        « EXEMPLE MÉCANIQUE »), accents and plurals changed, initials glued to the next word (« Garage EXauto » for
        « Garage EX Auto »), the trade word Google adds left out (« JX Services Sàrl » for « Garage JX services »).
        The name, the name without its trade words, its glued spellings, then each of its distinctive words, is
        searched; a firm
        counts when all the words of the shorter name are in the other one and one of its addresses (the
        registered one, or another its publications give, where a workshop away from the seat is) has the
        business's postal code or town, the firms sharing the most words read first. It only names the head: an
        exact match alone may tell that the business closed.

        Args:
            name: The business name.
            town: The business's town.
            postal_code: The business's postal code, when known.

        Returns:
            The only such firm; ``None`` when none or several are.
        """
        if not town and not postal_code:
            return None
        named: dict[str, SwissRegisterFirm] = {}
        queries = dict.fromkeys(
            query
            for query in (
                self.register_name(name),
                self._trade_free_name(name),
                *self._glued_spellings(name),
                *self._searched_words(name, town),
            )
            if query
        )
        for query in queries:
            for firm in await self.firms_named(query, max_entries=_MAX_FIRMS_PER_WORD):
                if firm.status == _ACTIVE_STATUS and firm.uid and self.shares_words(firm.name, name, town=town):
                    named.setdefault(firm.uid, firm)
        business_words = BusinessName.distinctive_stems(name, town=town)
        closest_first = sorted(
            named.values(),
            key=lambda firm: len(
                BusinessName.distinctive_stems(BusinessName.clean(firm.name), town=town) & business_words
            ),
            reverse=True,
        )
        at_address: list[SwissRegisterFirm] = []
        for firm in closest_first[:_MAX_ADDRESSES_READ]:
            for firm_postal_code, firm_town in await self.addresses_of(firm):
                is_same_postal_code = bool(postal_code) and firm_postal_code == postal_code
                is_same_town = bool(town and firm_town) and town_key(firm_town or "") == town_key(town or "")
                if is_same_postal_code or is_same_town:
                    at_address.append(firm)
                    break
        return at_address[0] if len(at_address) == 1 else None

    @staticmethod
    def shares_words(firm_name: str, business_name: str, *, town: str | None) -> bool:
        """
        Whether a firm's name and a business name have the same distinctive words, the longer one adding some.

        « GLF Mécanique Lopes » holds « GLF MÉCANIQUE », « Exemple Électricité-Telecom » holds the words of
        « Exemple Eletricite-Telecom » but its misspelled trade; the owner's name after a comma or a dash
        (« Garage des Deux Cantons, Modèle Jules ») is left out.

        Args:
            firm_name: The firm's name in the register.
            business_name: The business name.
            town: The business's town, left out of both.

        Returns:
            True when the words of one name are all in the other.
        """
        firm_words = BusinessName.distinctive_stems(BusinessName.clean(firm_name), town=town)
        business_words = BusinessName.distinctive_stems(business_name, town=town)
        if not firm_words or not business_words:
            return False
        if firm_words <= business_words or business_words <= firm_words:
            return True
        glued_firm_name = SwissRegistry._compact_beside_trade(BusinessName.clean(firm_name))
        return bool(glued_firm_name) and glued_firm_name == SwissRegistry._compact_beside_trade(business_name)

    @staticmethod
    def _searched_words(name: str, town: str | None) -> list[str]:
        """The distinctive words of a name worth a register search on their own, longest first."""
        words = sorted(BusinessName.distinctive_words(name, town=town), key=lambda word: (-len(word), word))
        return [word for word in words if len(word) >= 3][:_MAX_SEARCHED_WORDS]

    @classmethod
    def _trade_free_name(cls, name: str) -> str:
        """A name without its trade words, the way the register may file it (« JX services » for « Garage JX services »)."""
        from services.prospect_search.trade_catalog import TradeCatalog

        words = cls.register_name(name).split()
        return " ".join(word for word in words if not TradeCatalog.is_trade_word(fold(word)))

    @staticmethod
    def _glued_spellings(name: str) -> list[str]:
        """The name with its initials glued to the next word, the way the register may file it (« EXauto »)."""
        words = BusinessName.without_legal_form(name).split()
        return [
            f"{word}{following}"
            for word, following in pairwise(words)
            if _INITIALS_TOKEN_RE.match(word) and following[:1].isalpha()
        ]

    @staticmethod
    def _compact_beside_trade(name: str) -> str:
        """A name's letters and digits without its legal form and trade words (« Garage EX Auto » gives « exauto »)."""
        from services.prospect_search.trade_catalog import TradeCatalog

        words = re.findall(r"[a-z0-9]+", fold(BusinessName.without_legal_form(name)))
        return "".join(word for word in words if not TradeCatalog.is_trade_word(word))

    async def publications(self, firm: SwissRegisterFirm) -> list[tuple[date, str]]:
        """
        The firm's publications in the official gazette (FOSC), each with its date.

        Args:
            firm: A firm the register listed.

        Returns:
            ``(date, text)`` of each publication; empty when the register does not answer.
        """
        publications: list[tuple[date, str]] = []
        for publication in (await self._detail(firm)).get("shabPub") or []:
            published_on = str(publication.get("shabDate") or "")
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", published_on):
                publications.append((date.fromisoformat(published_on), str(publication.get("message") or "")))
        return publications

    async def excerpt_people(self, firm: SwissRegisterFirm) -> list[RegisteredPerson]:
        """
        The people a firm's cantonal register excerpt lists today, for a firm whose FOSC publications name nobody.

        Zefix links each firm to its canton's excerpt. Vaud, Geneva, Fribourg and Neuchâtel run the same software:
        its catalog sets an anti-forgery cookie, then the excerpt is asked with that token, as the excerpt's own page
        does. Valais and Jura run another one, not read.

        Args:
            firm: A firm the register listed.

        Returns:
            The active people; empty when the canton's software is another or does not answer.
        """
        from services.website_liveness_service import website_liveness_service

        excerpt_url = str((await self._detail(firm)).get("cantonalExcerptWeb") or "")
        if _EXCERPT_PATH not in excerpt_url or not firm.uid:
            return []
        base = excerpt_url.split(_EXCERPT_PATH, 1)[0]
        page = urlparse(excerpt_url)
        request = {**_EXCERPT_REQUEST, "companyOfsUid": firm.uid}
        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT_SECONDS, follow_redirects=True, headers=website_liveness_service.REQUEST_HEADERS
            ) as http:
                await http.get(excerpt_url)
                await http.get(f"{base}/api/public/catalog/configuration")
                response = await http.post(
                    f"{base}/api/public/hrcexcerpts/",
                    json=request,
                    headers={
                        "X-XSRF-TOKEN": http.cookies.get(_XSRF_COOKIE) or "",
                        "Origin": f"{page.scheme}://{page.netloc}",
                        "Referer": excerpt_url,
                    },
                )
        except httpx.HTTPError as exc:
            logger.warning("Cantonal excerpt of %s failed: %s", firm.name, exc)
            return []
        if response.status_code != 200:
            return []
        payload = response.json()
        excerpt = payload[0] if isinstance(payload, list) and payload else payload
        return SwissRegisterPeople.excerpt_people(excerpt.get("adms") or []) if isinstance(excerpt, dict) else []

    async def address_of(self, firm: SwissRegisterFirm) -> tuple[str | None, str | None]:
        """
        The postal code and town of a firm's registered address, which a village business shares with its firm.

        Args:
            firm: A firm the register listed.

        Returns:
            ``(postal code, town)``, each None when the register does not say or does not answer.
        """
        addresses = await self.addresses_of(firm)
        return addresses[0] if addresses else (None, None)

    async def addresses_of(self, firm: SwissRegisterFirm) -> list[tuple[str | None, str | None]]:
        """
        The postal codes and towns where a firm works: its registered address, then the other addresses its
        publications give (« Autre adresse: Route Exemple 28, 1880 Bex »), where a workshop away from the seat is.

        Args:
            firm: A firm the register listed.

        Returns:
            ``(postal code, town)`` of each address, the registered one first; empty when the register does not answer.
        """
        detail = await self._detail(firm)
        if not detail:
            return []
        address = detail.get("address") or {}
        town = _CANTON_SUFFIX_RE.sub("", str(address.get("town") or "").strip())
        addresses: list[tuple[str | None, str | None]] = [
            (str(address.get("swissZipCode") or "") or None, town or None)
        ]
        for publication in detail.get("shabPub") or []:
            text = re.sub(r"<[^>]+>", "", str(publication.get("message") or ""))
            addresses += [
                (postal_code, other_town.strip()) for postal_code, other_town in _OTHER_ADDRESS_RE.findall(text)
            ]
        return addresses

    async def _detail(self, firm: SwissRegisterFirm) -> dict[str, Any]:
        """The register's page of a firm (address, publications); empty when unknown or the register does not answer."""
        if firm.register_id is None:
            return {}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http:
                response = await http.get(_FIRM_URL.format(register_id=firm.register_id))
        except httpx.HTTPError as exc:
            logger.warning("Zefix page of %s failed: %s", firm.name, exc)
            return {}
        return response.json() if response.status_code == 200 else {}

    @staticmethod
    def register_name(name: str) -> str:
        """The words the register files a business under: no legal form, no civility (« Mr. »)."""
        return BusinessName.without_legal_form(_HONORIFIC_RE.sub("", name))

    @staticmethod
    def closing_words(firm: SwissRegisterFirm) -> str | None:
        """How a firm is closed: in liquidation, or struck off lately; ``None`` when it is not."""
        if firm.status == _IN_LIQUIDATION_STATUS:
            return "en liquidation"
        is_recent = firm.struck_off_on is not None and (
            datetime.now(UTC).date() - firm.struck_off_on <= _RECENT_STRIKING_OFF
        )
        return "radiée" if firm.status == _STRUCK_OFF_STATUS and is_recent else None

    @classmethod
    def _compact(cls, name: str) -> str:
        """A name reduced to its letters and digits, without legal form, civility nor « en liquidation »."""
        return re.sub(r"[^a-z0-9]", "", fold(cls.register_name(_LIQUIDATION_SUFFIX_RE.sub("", name))))


swiss_registry = SwissRegistry()
