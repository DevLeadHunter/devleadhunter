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

import httpx

from services.decision_maker.normalize import fold
from services.prospect_search.business_name import BusinessName
from services.prospect_search.candidate_facts import CandidateFacts

logger = logging.getLogger(__name__)

_SEARCH_URL: str = "https://www.zefix.ch/ZefixREST/api/v1/firm/search.json"
_TIMEOUT_SECONDS: float = 15.0
_MAX_FIRMS: int = 10
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


@dataclass(frozen=True)
class SwissRegisterFirm:
    """A firm as the federal register lists it."""

    name: str
    seat: str
    status: str
    uid: str
    struck_off_on: date | None = None


class SwissRegistry:
    """Reads the federal company register for the closing of a Swiss business."""

    async def read_closing(self, facts: CandidateFacts) -> None:
        """
        Take the register's « en liquidation » or recent « radiée » as the closing of a Swiss company.

        Only a firm of the same name, legal form and civility aside, at the same seat counts; an
        active one of that name and seat clears the business, and gives its company number when
        it has none.

        Args:
            facts: The candidate, completed in place.
        """
        if facts.country != "CH" or facts.is_closed or not facts.town:
            return
        firms = [
            firm
            for firm in await self.firms_named(self.register_name(facts.name))
            if self.is_same_firm(firm, name=facts.name, town=facts.town)
        ]
        active = next((firm for firm in firms if firm.status == _ACTIVE_STATUS), None)
        if active is not None:
            if not facts.registry_number and active.uid:
                facts.registry_number = active.uid
                facts.add_evidence("registry", active.uid, source=_REGISTER_SOURCE)
            return
        closing = next((words for firm in firms if (words := self._closing_words(firm)) is not None), None)
        if closing is not None:
            facts.is_closed = True
            facts.add_evidence("closed", closing, source=_REGISTER_SOURCE)

    async def firms_named(self, name: str) -> list[SwissRegisterFirm]:
        """
        The firms whose name contains *name*, struck off ones included, as the register lists them.

        Args:
            name: The business name, without its legal form nor civility.

        Returns:
            The firms; empty when the register lists none or does not answer.
        """
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http:
                response = await http.post(
                    _SEARCH_URL,
                    json={"name": name, "languageKey": "fr", "maxEntries": _MAX_FIRMS, "deletedFirms": True},
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
            )
            for firm in response.json().get("list") or []
        ]

    @staticmethod
    def register_name(name: str) -> str:
        """The words the register files a business under: no legal form, no civility (« Mr. »)."""
        return BusinessName.without_legal_form(_HONORIFIC_RE.sub("", name))

    @classmethod
    def is_same_firm(cls, firm: SwissRegisterFirm, *, name: str, town: str) -> bool:
        """Whether a register firm is the business: the same name, legal form and civility aside, at the same seat."""
        return fold(firm.seat) == fold(town) and cls._compact(firm.name) == cls._compact(name)

    @staticmethod
    def _closing_words(firm: SwissRegisterFirm) -> str | None:
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
