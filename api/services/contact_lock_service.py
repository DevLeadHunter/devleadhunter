"""Cross-module contact lock — never approach the same prospect for two offers at once.

When a sellable module (a website campaign, an AI-assistant campaign, a cold SMS…) engages a
prospect, it stamps ``prospect.contacted_by_module`` / ``contacted_by_module_at``. For the next
``LOCK_DAYS`` days the *other* modules skip that prospect, so he finishes one module's sequence
before another can start. A module is never blocked by its own stamp — its own follow-ups run.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from models.prospect_db import ProspectDB

# The sellable modules. Values match the web's ``DlhModuleKey`` so the two sides agree.
MODULE_WEBSITES = "websites"
MODULE_AI_ASSISTANT = "ai-assistant"

# How long one module's contact reserves a prospect against the others. A full sequence (first
# email + follow-ups + the J+30 relance) runs ~30-40 days, so 45 days lets a prospect finish one
# module's outreach before another module may start.
LOCK_DAYS = 45

_MODULE_LABELS: dict[str, str] = {
    MODULE_WEBSITES: "Sites web",
    MODULE_AI_ASSISTANT: "Assistant IA",
}


class ContactLockService:
    """Reads and writes the cross-module contact lock carried by a prospect."""

    @staticmethod
    def is_locked_for_module(prospect: ProspectDB, module: str, now: datetime) -> bool:
        """Whether *module* must skip this prospect because another module engaged him recently.

        Args:
            prospect: The prospect about to be contacted.
            module: The module that wants to contact him.
            now: The current UTC time.

        Returns:
            True when a *different* module stamped him inside the lock window.
        """
        other: str | None = prospect.contacted_by_module
        at: datetime | None = prospect.contacted_by_module_at
        if not other or at is None or other == module:
            return False
        return now - at < timedelta(days=LOCK_DAYS)

    @staticmethod
    def record_contact(prospect: ProspectDB, module: str, now: datetime) -> None:
        """Stamp that *module* engaged this prospect at *now* (the caller commits).

        Args:
            prospect: The prospect being contacted.
            module: The module doing the contact.
            now: The current UTC time.
        """
        prospect.contacted_by_module = module
        prospect.contacted_by_module_at = now

    @staticmethod
    def locked_until(prospect: ProspectDB, now: datetime) -> datetime | None:
        """When the current lock lifts, or None when the prospect is not (or no longer) locked.

        Args:
            prospect: The prospect to inspect.
            now: The current UTC time.

        Returns:
            The lock's lift time when it is still in the future, else None.
        """
        at: datetime | None = prospect.contacted_by_module_at
        if not prospect.contacted_by_module or at is None:
            return None
        lifts: datetime = at + timedelta(days=LOCK_DAYS)
        return lifts if lifts > now else None

    @staticmethod
    def module_label(module: str | None) -> str:
        """A human label for a module key (``'websites'`` -> ``'Sites web'``)."""
        return _MODULE_LABELS.get(module or "", module or "")


contact_lock_service = ContactLockService()
